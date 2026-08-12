
import { execSync } from 'child_process';

const url = 'https://www.lalsace.fr/culture-loisirs/2026/01/28/on-fait-quoi-ce-week-end-du-30-janvier-au-1er-fevrier-dans-le-sud-alsace';

try {
    console.log(`Analyse des balises meta pour : ${url}`);
    const html = execSync(`curl -s -L "${url}"`, { encoding: 'utf-8', maxBuffer: 1024 * 1024 * 5 });
    
    const ogDesc = html.match(/property="og:description" content="(.*?)"/);
    const metaDesc = html.match(/name="description" content="(.*?)"/);
    
    console.log(`og:description: ${ogDesc ? ogDesc[1] : 'NON TROUVÉ'}`);
    console.log(`meta description: ${metaDesc ? metaDesc[1] : 'NON TROUVÉ'}`);

    if (!ogDesc && !metaDesc) {
        console.log("\nConfirmation : Cet article n'a AUCUNE balise de description meta.");
        // Regardons si on trouve un chapo ou un premier paragraphe
        const chapo = html.match(/class="chapo">(.*?)<\/div>/);
        console.log(`Chapo trouvé dans HTML: ${chapo ? 'OUI' : 'NON'}`);
    }
} catch (error) {
    console.error('Erreur :', error.message);
}

