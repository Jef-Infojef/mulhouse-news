"use client";

import React from "react";
import { m, useReducedMotion } from "framer-motion";
import { Logo } from "@/components/Logo";

interface SplashScreenProps {
  onFinish: () => void;
}

export function SplashScreen({ onFinish }: SplashScreenProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <m.div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950"
      initial={{ opacity: 1 }}
      animate={{ opacity: 0 }}
      transition={{ 
        duration: 0.8, 
        delay: shouldReduceMotion ? 1.0 : 2.2, // Attend que le zoom soit fini avant de fade out le fond
        ease: "easeOut" 
      }}
      onAnimationComplete={onFinish}
    >
      <div className="relative flex items-center justify-center w-full h-full overflow-hidden">
        <m.div
          initial={shouldReduceMotion ? { scale: 1, opacity: 0 } : { scale: 0.5, opacity: 0, rotate: -45 }}
          animate={shouldReduceMotion ? { opacity: 1 } : { 
            scale: [0.5, 1.2, 80], // Petit -> Normal -> ÉNORME
            opacity: [0, 1, 1],
            rotate: [0, 0, 0]
          }}
          transition={shouldReduceMotion ? { duration: 1 } : {
            duration: 2.5,
            times: [0, 0.4, 1], // Timing des étapes du scale
            ease: "easeInOut"
          }}
          className="relative z-10"
        >
          {/* On utilise une div conteneur pour s'assurer que le SVG reste net */}
          <div className="w-48 h-48 md:w-64 md:h-64">
             <Logo className="w-full h-full text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.3)]" />
          </div>
        </m.div>

        {/* Texte optionnel qui apparait brièvement */}
        <m.div
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
            animate={shouldReduceMotion ? { opacity: [0, 1, 0] } : { opacity: [0, 1, 0], y: [20, 0, -50] }}
            transition={{ duration: 1.5, delay: 0.5 }}
            className="absolute bottom-1/4 text-white text-2xl font-bold tracking-widest uppercase"
        >
            Mulhouse Actu
        </m.div>
      </div>
    </m.div>
  );
}
