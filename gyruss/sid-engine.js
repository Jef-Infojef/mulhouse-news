// ═══════════════════════════════════════════════════════════════
// SIDEngine - Emulateur SID 6581 + CPU 6510 minimal pour fichiers .sid
// Inspire de jsSID (Hermit) - adapte pour Web Audio API
// ═══════════════════════════════════════════════════════════════

class SIDEngine {
  constructor(data, sampleRate) {
    this.sampleRate = sampleRate;
    this.valid   = false;
    this.playing = false;
    this.title   = '';
    this.author  = '';
    this.mem     = new Uint8Array(65536);
    this.sid     = new SID6581(sampleRate);
    this.cpu     = new CPU6510(this.mem, this.sid);
    // CIA timer 50Hz PAL
    this.palClock    = 985248;
    this.cyclesPerSample = this.palClock / sampleRate;
    this.cycleAccum  = 0;
    this.ciaTimer    = Math.round(this.palClock / 50);
    this.ciaCount    = this.ciaTimer;
    this.initAddr    = 0;
    this.playAddr    = 0;
    this._parse(data);
  }

  _parse(data) {
    const magic = String.fromCharCode(data[0],data[1],data[2],data[3]);
    if (magic !== 'PSID' && magic !== 'RSID') return;
    const v = new DataView(data.buffer, data.byteOffset);
    const dataOff  = v.getUint16(6);
    let   loadAddr = v.getUint16(8);
    this.initAddr  = v.getUint16(10);
    this.playAddr  = v.getUint16(12);
    this.songs     = v.getUint16(14);
    this.startSong = Math.max(0, v.getUint16(16) - 1);
    const dec = new TextDecoder('latin1');
    this.title  = dec.decode(data.slice(22,54)).replace(/\0.*/,'');
    this.author = dec.decode(data.slice(54,86)).replace(/\0.*/,'');
    // Load PRG
    let off = dataOff;
    if (loadAddr === 0) { loadAddr = data[off] | (data[off+1]<<8); off += 2; }
    for (let i = off; i < data.length; i++) this.mem[loadAddr + (i-off)] = data[i];
    // C64 memory setup
    this.mem[0x01] = 0x37;
    this.valid = true;
    this.play(this.startSong);
  }

  play(subtune) {
    this.sid.reset();
    this.cpu.reset();
    this.cpu.callSubroutine(this.initAddr, subtune & 0xFF);
    this.ciaCount = this.ciaTimer;
    this.playing  = true;
  }

  stop() { this.playing = false; }

  clock() {
    if (!this.playing) return 0;
    this.cycleAccum += this.cyclesPerSample;
    let cycles = Math.floor(this.cycleAccum);
    this.cycleAccum -= cycles;
    while (cycles-- > 0) {
      this.sid.clock();
      this.ciaCount--;
      if (this.ciaCount <= 0) {
        this.ciaCount = this.ciaTimer;
        if (this.playAddr !== 0) this.cpu.callSubroutine(this.playAddr, 0);
      }
    }
    return this.sid.output();
  }
}

// ═══════════════════════════════════════════════════════════════
// SID 6581 Chip Emulator
// ═══════════════════════════════════════════════════════════════
class SID6581 {
  constructor(sampleRate) {
    this.sr = sampleRate;
    this.reg = new Uint8Array(29);
    this.v = [new SIDVoice(), new SIDVoice(), new SIDVoice()];
    this.flt = new SIDFilter();
    this.reset();
  }
  reset() {
    this.reg.fill(0);
    this.v.forEach(v => v.reset());
    this.flt.reset();
    this.vol = 0;
  }
  write(addr, val) {
    const a = addr & 0x1F;
    this.reg[a] = val;
    const vi = (a / 7) | 0;
    const ri = a % 7;
    if (vi < 3) {
      const v = this.v[vi];
      switch (ri) {
        case 0: v.freqLo  = val; v.freq = (v.freqHi<<8)|v.freqLo; break;
        case 1: v.freqHi  = val; v.freq = (v.freqHi<<8)|v.freqLo; break;
        case 2: v.pwLo    = val; v.pw   = ((v.pwHi&0xF)<<8)|v.pwLo; break;
        case 3: v.pwHi    = val; v.pw   = ((v.pwHi&0xF)<<8)|v.pwLo; break;
        case 4: v.setCtrl(val); break;
        case 5: v.setAD(val); break;
        case 6: v.setSR(val); break;
      }
    } else if (a === 21) this.flt.setFreqLo(val);
    else if (a === 22) this.flt.setFreqHi(val);
    else if (a === 23) this.flt.setRes(val);
    else if (a === 24) { this.flt.setMode(val); this.vol = val & 0xF; }
  }
  read(addr) { return this.reg[addr & 0x1F]; }
  clock() { this.v.forEach(v => v.clock()); }
  output() {
    let s = 0;
    for (let i = 0; i < 3; i++) {
      const v = this.v[i];
      if (v.mute) continue;
      s += v.sample();
    }
    s = Math.max(-32767, Math.min(32767, (s * this.vol) >> 2));
    return this.flt.process(s);
  }
}

class SIDVoice {
  constructor() { this.reset(); }
  reset() {
    this.freq=0; this.freqLo=0; this.freqHi=0;
    this.pw=0x800; this.pwLo=0; this.pwHi=0;
    this.phase=0; this.acc=0;
    this.waveform=0; this.gate=false; this.sync=false; this.ring=false; this.test=false; this.mute=false;
    this.attack=0; this.decay=0; this.sustain=0; this.release=0;
    this.env=0; this.envPhase=0; // 0=release,1=attack,2=decay,3=sustain
    this.envCount=0; this.envRate=0;
    this.noise=0x7FFFF8; this.noiseBit=0;
  }
  setCtrl(v) {
    const prevGate = this.gate;
    this.waveform = (v >> 4) & 0xF;
    this.test     = !!(v & 8);
    this.ring     = !!(v & 4);
    this.sync     = !!(v & 2);
    this.gate     = !!(v & 1);
    this.mute     = this.waveform === 0;
    if (this.gate && !prevGate) this.envPhase = 1; // attack
    if (!this.gate && prevGate) this.envPhase = 0; // release
  }
  setAD(v) {
    this.attack  = SIDVoice.AR_TABLE[(v>>4)&0xF];
    this.decay   = SIDVoice.DR_TABLE[v&0xF];
  }
  setSR(v) {
    this.sustain = ((v>>4)&0xF) * 0x1111;
    this.release = SIDVoice.DR_TABLE[v&0xF];
  }
  clock() {
    // Phase accumulator
    if (this.test) this.acc = 0;
    else this.acc = (this.acc + this.freq) & 0xFFFFFF;
    // Noise LFSR clock (every 32nd cycle approx)
    if ((this.acc & 0x80000) !== (this.phase & 0x80000)) {
      const n = this.noise;
      this.noise = (n<<1)&0x7FFFFF | (((n>>22)^(n>>17))&1);
    }
    this.phase = this.acc;
    // Envelope
    this.envCount++;
    let rate = 0;
    if (this.envPhase===1) rate = this.attack;
    else if (this.envPhase===2) rate = this.decay;
    else if (this.envPhase===0) rate = this.release;
    if (this.envCount >= rate) {
      this.envCount = 0;
      if (this.envPhase===1) { // attack
        this.env++; if (this.env >= 0xFF) { this.env=0xFF; this.envPhase=2; }
      } else if (this.envPhase===2) { // decay
        if (this.env > this.sustain) this.env--;
        else this.envPhase=3;
      } else if (this.envPhase===0) { // release
        if (this.env > 0) this.env--;
      }
    }
  }
  sample() {
    const ph = this.acc >> 12; // 0..4095
    let w = 0;
    if (this.waveform & 8) { // noise
      w = ((this.noise>>4)&0xFFE) - 0x800;
    } else if (this.waveform & 4) { // pulse
      w = (ph < this.pw) ? 0xFFF : 0;
    } else if (this.waveform & 2) { // sawtooth
      w = ph;
    } else if (this.waveform & 1) { // triangle
      w = (ph < 0x800) ? ph*2 : (0xFFF - ph)*2;
    }
    if (this.waveform === 3) w = (w & ((ph<this.pw)?0xFFF:0)); // pulse+saw
    w = (w - 0x800) * 16; // center around 0, scale
    return (w * this.env) >> 8;
  }
}
// Attack rates in clock cycles at 1MHz
SIDVoice.AR_TABLE = [9,32,63,95,149,220,267,313,392,977,1954,3126,3906,11720,19531,31250];
SIDVoice.DR_TABLE = [9,32,63,95,149,220,267,313,392,977,1954,3126,3906,11720,19531,31250];

class SIDFilter {
  constructor() { this.reset(); }
  reset() { this.freq=0; this.res=0; this.mode=0; this.vol=0; this.lp=0; this.bp=0; this.hp=0; }
  setFreqLo(v) { this.freq = (this.freq&0x7F8)|(v&7); this._calc(); }
  setFreqHi(v) { this.freq = (v<<3)|(this.freq&7); this._calc(); }
  setRes(v) { this.res = (v>>4)&0xF; this.mode = v&0xF; }
  setMode(v) { this.mode = v; }
  _calc() { this.f = 2*Math.PI*this.freq*40/(985248); this.q = 1/(0.5+this.res*0.1+0.05); }
  process(s) {
    // Simple state-variable filter
    const f = this.f || 0.01, q = this.q || 1;
    this.lp += f * this.bp;
    this.hp  = s - this.lp - q * this.bp;
    this.bp += f * this.hp;
    // Mode bits: 1=LP, 2=BP, 4=HP
    let out = 0;
    if (this.mode & 1) out += this.lp;
    if (this.mode & 2) out += this.bp;
    if (this.mode & 4) out += this.hp;
    return (this.mode & 7) ? Math.max(-32767,Math.min(32767,out)) : s;
  }
}

// ═══════════════════════════════════════════════════════════════
// CPU 6510 - Emulateur minimal pour execution des routines SID
// Supporte uniquement les opcodes necessaires aux tunes SID
// ═══════════════════════════════════════════════════════════════
class CPU6510 {
  constructor(mem, sid) {
    this.mem = mem;
    this.sid = sid;
    this.reset();
  }
  reset() {
    this.A=0; this.X=0; this.Y=0; this.SP=0xFF; this.PC=0;
    this.N=0; this.V=0; this.B=0; this.D=0; this.I=1; this.Z=0; this.C=0;
    this.cycles=0;
  }

  r(addr) {
    addr &= 0xFFFF;
    if (addr >= 0xD400 && addr <= 0xD41C) return this.sid.read(addr - 0xD400);
    return this.mem[addr];
  }
  w(addr, val) {
    addr &= 0xFFFF; val &= 0xFF;
    if (addr >= 0xD400 && addr <= 0xD41C) { this.sid.write(addr - 0xD400, val); return; }
    this.mem[addr] = val;
  }
  rb(addr) { return this.r(addr) | (this.r((addr+1)&0xFFFF)<<8); }
  push(v) { this.w(0x100|this.SP, v); this.SP=(this.SP-1)&0xFF; }
  pop()   { this.SP=(this.SP+1)&0xFF; return this.r(0x100|this.SP); }

  setNZ(v) { this.N=(v>>7)&1; this.Z=(v===0)?1:0; return v; }

  // Execute until RTS from the top-level call (max 100000 cycles safety)
  callSubroutine(addr, arg) {
    this.A = arg & 0xFF;
    this.X = 0; this.Y = 0;
    this.PC = addr & 0xFFFF;
    // Push fake return address $FFFF: RTS does PC = (hi<<8|lo)+1 = 0xFFFF+1 = 0x10000 → stop
    this.push(0xFF); this.push(0xFF);
    for (let guard = 0; guard < 100000; guard++) {
      if (!this.step()) break;
    }
  }

  step() {
    const op = this.r(this.PC); this.PC=(this.PC+1)&0xFFFF;
    switch(op) {
      // ── Load/Store ──
      case 0xA9: this.A=this.setNZ(this.r(this.PC++)); break; // LDA imm
      case 0xA5: this.A=this.setNZ(this.r(this.r(this.PC++))); break; // LDA zp
      case 0xB5: this.A=this.setNZ(this.r((this.r(this.PC++)+this.X)&0xFF)); break; // LDA zp,X
      case 0xAD: { const a=this.rb(this.PC);this.PC+=2;this.A=this.setNZ(this.r(a)); break; } // LDA abs
      case 0xBD: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.r(a)); break; }
      case 0xB9: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.r(a)); break; }
      case 0xA1: { const z=(this.r(this.PC++)+this.X)&0xFF;this.A=this.setNZ(this.r(this.rb(z))); break; }
      case 0xB1: { const z=this.r(this.PC++);this.A=this.setNZ(this.r((this.rb(z)+this.Y)&0xFFFF)); break; }
      case 0xA2: this.X=this.setNZ(this.r(this.PC++)); break; // LDX imm
      case 0xA6: this.X=this.setNZ(this.r(this.r(this.PC++))); break;
      case 0xB6: this.X=this.setNZ(this.r((this.r(this.PC++)+this.Y)&0xFF)); break;
      case 0xAE: { const a=this.rb(this.PC);this.PC+=2;this.X=this.setNZ(this.r(a)); break; }
      case 0xBE: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;this.X=this.setNZ(this.r(a)); break; }
      case 0xA0: this.Y=this.setNZ(this.r(this.PC++)); break; // LDY imm
      case 0xA4: this.Y=this.setNZ(this.r(this.r(this.PC++))); break;
      case 0xB4: this.Y=this.setNZ(this.r((this.r(this.PC++)+this.X)&0xFF)); break;
      case 0xAC: { const a=this.rb(this.PC);this.PC+=2;this.Y=this.setNZ(this.r(a)); break; }
      case 0xBC: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.Y=this.setNZ(this.r(a)); break; }
      case 0x85: this.w(this.r(this.PC++),this.A); break; // STA zp
      case 0x95: this.w((this.r(this.PC++)+this.X)&0xFF,this.A); break;
      case 0x8D: { const a=this.rb(this.PC);this.PC+=2;this.w(a,this.A); break; } // STA abs
      case 0x9D: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.w(a,this.A); break; }
      case 0x99: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;this.w(a,this.A); break; }
      case 0x81: { const z=(this.r(this.PC++)+this.X)&0xFF;this.w(this.rb(z),this.A); break; }
      case 0x91: { const z=this.r(this.PC++);this.w((this.rb(z)+this.Y)&0xFFFF,this.A); break; }
      case 0x86: this.w(this.r(this.PC++),this.X); break; // STX zp
      case 0x96: this.w((this.r(this.PC++)+this.Y)&0xFF,this.X); break;
      case 0x8E: { const a=this.rb(this.PC);this.PC+=2;this.w(a,this.X); break; }
      case 0x84: this.w(this.r(this.PC++),this.Y); break; // STY zp
      case 0x94: this.w((this.r(this.PC++)+this.X)&0xFF,this.Y); break;
      case 0x8C: { const a=this.rb(this.PC);this.PC+=2;this.w(a,this.Y); break; }
      // ── Transfer ──
      case 0xAA: this.X=this.setNZ(this.A); break; // TAX
      case 0xA8: this.Y=this.setNZ(this.A); break; // TAY
      case 0x8A: this.A=this.setNZ(this.X); break; // TXA
      case 0x98: this.A=this.setNZ(this.Y); break; // TYA
      case 0x9A: this.SP=this.X; break;            // TXS
      case 0xBA: this.X=this.setNZ(this.SP); break;// TSX
      // ── Stack ──
      case 0x48: this.push(this.A); break;          // PHA
      case 0x68: this.A=this.setNZ(this.pop()); break; // PLA
      case 0x08: { let p=(this.N<<7)|(this.V<<6)|0x30|(this.D<<3)|(this.I<<2)|(this.Z<<1)|this.C; this.push(p); break; }
      case 0x28: { const p=this.pop(); this.N=(p>>7)&1;this.V=(p>>6)&1;this.D=(p>>3)&1;this.I=(p>>2)&1;this.Z=(p>>1)&1;this.C=p&1; break; }
      // ── Arithmetic ──
      case 0x69: { const v=this.r(this.PC++);const r=this.A+v+this.C;this.V=((~(this.A^v)&(this.A^r))>>7)&1;this.C=(r>255)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0x65: { const v=this.r(this.r(this.PC++));const r=this.A+v+this.C;this.V=((~(this.A^v)&(this.A^r))>>7)&1;this.C=(r>255)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0x6D: { const a=this.rb(this.PC);this.PC+=2;const v=this.r(a);const r=this.A+v+this.C;this.V=((~(this.A^v)&(this.A^r))>>7)&1;this.C=(r>255)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0x7D: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const v=this.r(a);const r=this.A+v+this.C;this.V=((~(this.A^v)&(this.A^r))>>7)&1;this.C=(r>255)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0x79: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;const v=this.r(a);const r=this.A+v+this.C;this.V=((~(this.A^v)&(this.A^r))>>7)&1;this.C=(r>255)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0xE9: { const v=this.r(this.PC++);const r=this.A-v-(1-this.C);this.V=(((this.A^v)&(this.A^r))>>7)&1;this.C=(r>=0)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0xE5: { const v=this.r(this.r(this.PC++));const r=this.A-v-(1-this.C);this.V=(((this.A^v)&(this.A^r))>>7)&1;this.C=(r>=0)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0xED: { const a=this.rb(this.PC);this.PC+=2;const v=this.r(a);const r=this.A-v-(1-this.C);this.V=(((this.A^v)&(this.A^r))>>7)&1;this.C=(r>=0)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0xFD: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const v=this.r(a);const r=this.A-v-(1-this.C);this.V=(((this.A^v)&(this.A^r))>>7)&1;this.C=(r>=0)?1:0;this.A=this.setNZ(r&0xFF); break; }
      case 0xF9: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;const v=this.r(a);const r=this.A-v-(1-this.C);this.V=(((this.A^v)&(this.A^r))>>7)&1;this.C=(r>=0)?1:0;this.A=this.setNZ(r&0xFF); break; }
      // ── Inc/Dec ──
      case 0xE8: this.X=this.setNZ((this.X+1)&0xFF); break; // INX
      case 0xC8: this.Y=this.setNZ((this.Y+1)&0xFF); break; // INY
      case 0xCA: this.X=this.setNZ((this.X-1)&0xFF); break; // DEX
      case 0x88: this.Y=this.setNZ((this.Y-1)&0xFF); break; // DEY
      case 0xE6: { const a=this.r(this.PC++);this.w(a,this.setNZ((this.r(a)+1)&0xFF)); break; }
      case 0xEE: { const a=this.rb(this.PC);this.PC+=2;this.w(a,this.setNZ((this.r(a)+1)&0xFF)); break; }
      case 0xFE: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.w(a,this.setNZ((this.r(a)+1)&0xFF)); break; }
      case 0xC6: { const a=this.r(this.PC++);this.w(a,this.setNZ((this.r(a)-1)&0xFF)); break; }
      case 0xCE: { const a=this.rb(this.PC);this.PC+=2;this.w(a,this.setNZ((this.r(a)-1)&0xFF)); break; }
      case 0xDE: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.w(a,this.setNZ((this.r(a)-1)&0xFF)); break; }
      case 0xD6: { const a=(this.r(this.PC++)+this.X)&0xFF;this.w(a,this.setNZ((this.r(a)-1)&0xFF)); break; }
      case 0xF6: { const a=(this.r(this.PC++)+this.X)&0xFF;this.w(a,this.setNZ((this.r(a)+1)&0xFF)); break; }
      // ── Logic ──
      case 0x29: this.A=this.setNZ(this.A&this.r(this.PC++)); break; // AND imm
      case 0x25: this.A=this.setNZ(this.A&this.r(this.r(this.PC++))); break;
      case 0x2D: { const a=this.rb(this.PC);this.PC+=2;this.A=this.setNZ(this.A&this.r(a)); break; }
      case 0x3D: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.A&this.r(a)); break; }
      case 0x39: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.A&this.r(a)); break; }
      case 0x09: this.A=this.setNZ(this.A|this.r(this.PC++)); break; // ORA imm
      case 0x05: this.A=this.setNZ(this.A|this.r(this.r(this.PC++))); break;
      case 0x0D: { const a=this.rb(this.PC);this.PC+=2;this.A=this.setNZ(this.A|this.r(a)); break; }
      case 0x1D: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.A|this.r(a)); break; }
      case 0x19: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.A|this.r(a)); break; }
      case 0x49: this.A=this.setNZ(this.A^this.r(this.PC++)); break; // EOR imm
      case 0x45: this.A=this.setNZ(this.A^this.r(this.r(this.PC++))); break;
      case 0x4D: { const a=this.rb(this.PC);this.PC+=2;this.A=this.setNZ(this.A^this.r(a)); break; }
      case 0x5D: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.A^this.r(a)); break; }
      case 0x59: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;this.A=this.setNZ(this.A^this.r(a)); break; }
      case 0x24: { const v=this.r(this.r(this.PC++));this.N=(v>>7)&1;this.V=(v>>6)&1;this.Z=(this.A&v)?0:1; break; } // BIT zp
      case 0x2C: { const a=this.rb(this.PC);this.PC+=2;const v=this.r(a);this.N=(v>>7)&1;this.V=(v>>6)&1;this.Z=(this.A&v)?0:1; break; }
      // ── Shift ──
      case 0x0A: { this.C=(this.A>>7)&1;this.A=this.setNZ((this.A<<1)&0xFF); break; } // ASL A
      case 0x06: { const a=this.r(this.PC++);const v=(this.r(a)<<1);this.C=(v>>8)&1;this.w(a,this.setNZ(v&0xFF)); break; }
      case 0x0E: { const a=this.rb(this.PC);this.PC+=2;const v=(this.r(a)<<1);this.C=(v>>8)&1;this.w(a,this.setNZ(v&0xFF)); break; }
      case 0x1E: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const v=(this.r(a)<<1);this.C=(v>>8)&1;this.w(a,this.setNZ(v&0xFF)); break; }
      case 0x4A: { this.C=this.A&1;this.A=this.setNZ(this.A>>1); break; } // LSR A
      case 0x46: { const a=this.r(this.PC++);const v=this.r(a);this.C=v&1;this.w(a,this.setNZ(v>>1)); break; }
      case 0x4E: { const a=this.rb(this.PC);this.PC+=2;const v=this.r(a);this.C=v&1;this.w(a,this.setNZ(v>>1)); break; }
      case 0x5E: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const v=this.r(a);this.C=v&1;this.w(a,this.setNZ(v>>1)); break; }
      case 0x2A: { const c=this.C;this.C=(this.A>>7)&1;this.A=this.setNZ(((this.A<<1)|c)&0xFF); break; } // ROL A
      case 0x26: { const a=this.r(this.PC++);const v=this.r(a);const c=this.C;this.C=(v>>7)&1;this.w(a,this.setNZ(((v<<1)|c)&0xFF)); break; }
      case 0x2E: { const a=this.rb(this.PC);this.PC+=2;const v=this.r(a);const c=this.C;this.C=(v>>7)&1;this.w(a,this.setNZ(((v<<1)|c)&0xFF)); break; }
      case 0x3E: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const v=this.r(a);const c=this.C;this.C=(v>>7)&1;this.w(a,this.setNZ(((v<<1)|c)&0xFF)); break; }
      case 0x6A: { const c=this.C;this.C=this.A&1;this.A=this.setNZ((this.A>>1)|(c<<7)); break; } // ROR A
      case 0x66: { const a=this.r(this.PC++);const v=this.r(a);const c=this.C;this.C=v&1;this.w(a,this.setNZ((v>>1)|(c<<7))); break; }
      case 0x6E: { const a=this.rb(this.PC);this.PC+=2;const v=this.r(a);const c=this.C;this.C=v&1;this.w(a,this.setNZ((v>>1)|(c<<7))); break; }
      case 0x7E: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const v=this.r(a);const c=this.C;this.C=v&1;this.w(a,this.setNZ((v>>1)|(c<<7))); break; }
      // ── Compare ──
      case 0xC9: { const r=this.A-this.r(this.PC++);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; } // CMP imm
      case 0xC5: { const r=this.A-this.r(this.r(this.PC++));this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xCD: { const a=this.rb(this.PC);this.PC+=2;const r=this.A-this.r(a);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xDD: { const a=(this.rb(this.PC)+this.X)&0xFFFF;this.PC+=2;const r=this.A-this.r(a);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xD9: { const a=(this.rb(this.PC)+this.Y)&0xFFFF;this.PC+=2;const r=this.A-this.r(a);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xE0: { const r=this.X-this.r(this.PC++);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; } // CPX
      case 0xE4: { const r=this.X-this.r(this.r(this.PC++));this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xEC: { const a=this.rb(this.PC);this.PC+=2;const r=this.X-this.r(a);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xC0: { const r=this.Y-this.r(this.PC++);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; } // CPY
      case 0xC4: { const r=this.Y-this.r(this.r(this.PC++));this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      case 0xCC: { const a=this.rb(this.PC);this.PC+=2;const r=this.Y-this.r(a);this.C=(r>=0)?1:0;this.setNZ(r&0xFF); break; }
      // ── Branch ──
      case 0x90: { const o=this.r(this.PC++);if(!this.C){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; } // BCC
      case 0xB0: { const o=this.r(this.PC++);if(this.C){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; }  // BCS
      case 0xF0: { const o=this.r(this.PC++);if(this.Z){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; }  // BEQ
      case 0xD0: { const o=this.r(this.PC++);if(!this.Z){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; } // BNE
      case 0x30: { const o=this.r(this.PC++);if(this.N){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; }  // BMI
      case 0x10: { const o=this.r(this.PC++);if(!this.N){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; } // BPL
      case 0x70: { const o=this.r(this.PC++);if(this.V){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; }  // BVS
      case 0x50: { const o=this.r(this.PC++);if(!this.V){this.PC=(this.PC+(o<128?o:o-256))&0xFFFF;} break; } // BVC
      // ── Jump ──
      case 0x4C: this.PC=this.rb(this.PC); break; // JMP abs
      case 0x6C: { const a=this.rb(this.PC);this.PC=this.rb(a); break; } // JMP (ind)
      case 0x20: { // JSR abs
        const lo=this.r(this.PC); const hi=this.r(this.PC+1);
        const target=(hi<<8)|lo;
        const ret=(this.PC+1)&0xFFFF; // address of last byte of JSR instruction
        this.push(ret>>8); this.push(ret&0xFF);
        this.PC=target; break;
      }
      case 0x60: { // RTS
        const lo=this.pop(); const hi=this.pop();
        this.PC=((hi<<8)|lo)+1;
        if (this.PC>=0x10000) return false; // fake return address sentinel
        this.PC&=0xFFFF;
        break;
      }
      case 0x40: { // RTI
        const p=this.pop(); this.N=(p>>7)&1;this.V=(p>>6)&1;this.D=(p>>3)&1;this.I=(p>>2)&1;this.Z=(p>>1)&1;this.C=p&1;
        const lo=this.pop(); const hi=this.pop(); this.PC=(hi<<8)|lo; break;
      }
      // ── Flags ──
      case 0x18: this.C=0; break; case 0x38: this.C=1; break;
      case 0x58: this.I=0; break; case 0x78: this.I=1; break;
      case 0xD8: this.D=0; break; case 0xF8: this.D=1; break;
      case 0xB8: this.V=0; break;
      // ── Misc ──
      case 0xEA: break; // NOP
      case 0x00: return false; // BRK - stop
      // ── Undocumented (common) ──
      case 0x1A: case 0x3A: case 0x5A: case 0x7A: case 0xDA: case 0xFA: break; // NOP variants
      case 0x80: case 0x82: case 0x89: case 0xC2: case 0xE2: this.PC++; break;  // SKB
      case 0x0C: case 0x1C: case 0x3C: case 0x5C: case 0x7C: case 0xDC: case 0xFC: this.PC+=2; break; // SKW
      default: break; // ignore unknown
    }
    return true;
  }
}
