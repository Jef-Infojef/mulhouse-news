const { createClient } = require('@libsql/client');
const fs = require('fs');

async function dump() {
    let url = process.argv[2];
    let authToken = process.argv[3];
    const outputFile = process.argv[4];

    if (!url || !outputFile) {
        console.error('Usage: node turso-dump.js <url> <token> <output_file>');
        process.exit(1);
    }

    // Nettoyage des guillemets
    url = url.trim().replace(/^["'](.+)["']$/, '$1');
    authToken = authToken ? authToken.trim().replace(/^["'](.+)["']$/, '$1') : '';

    // Nettoyage de l'URL pour Turso : supprimer sslmode=... car non supporté par libsql
    if (url.includes('sslmode=')) {
        url = url.replace(/[\?&]sslmode=[^&]+/, '');
        // Si on a supprimé le seul paramètre, on enlève le ? restant
        if (url.endsWith('?')) url = url.slice(0, -1);
    }

    const client = createClient({ url, authToken });
    const sqlStream = fs.createWriteStream(outputFile);

    try {
        console.log(`[*] Connexion a Turso...`);
        const tablesResult = await client.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';");
        const tables = tablesResult.rows.map(r => r.name);

        sqlStream.write('-- Backup Turso Export\n');
        sqlStream.write('PRAGMA foreign_keys=OFF;\n');
        sqlStream.write('BEGIN TRANSACTION;\n\n');

        let totalRows = 0;
        for (const table of tables) {
            const schemaResult = await client.execute(`SELECT sql FROM sqlite_master WHERE type='table' AND name='${table}';`);
            if (schemaResult.rows.length > 0) {
                sqlStream.write(schemaResult.rows[0].sql + ';\n');
            }

            const dataResult = await client.execute(`SELECT * FROM "${table}";`);
            const rowCount = dataResult.rows.length;
            totalRows += rowCount;
            console.log(`[*] Export : ${table.padEnd(30)} [${rowCount}]`);
            
            for (const row of dataResult.rows) {
                const columns = dataResult.columns;
                const values = columns.map(col => {
                    const val = row[col];
                    if (val === null) return 'NULL';
                    if (typeof val === 'string') return "'" + val.replace(/'/g, "''") + "'";
                    if (typeof val === 'object' && val !== null) {
                        try { return "X'" + Buffer.from(val).toString('hex') + "'"; } catch (e) { return "'" + JSON.stringify(val).replace(/'/g, "''") + "'"; }
                    }
                    return val;
                });
                sqlStream.write(`INSERT INTO "${table}" (${columns.map(c => `"${c}"`).join(', ')}) VALUES (${values.join(', ')});\n`);
            }
            sqlStream.write('\n');
        }

        sqlStream.write('COMMIT;\n');
        sqlStream.write('PRAGMA foreign_keys=ON;\n');
        console.log(`\n[OK] Termine : ${tables.length} tables.`);
    } catch (error) {
        console.error('[ERREUR] ' + error.message);
        process.exit(1);
    } finally {
        sqlStream.end();
        client.close();
    }
}
dump();
