'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, Vote, Calendar, MessageSquare, Info, Users } from 'lucide-react';
import Link from 'next/link';
import { Logo } from '@/components/Logo';

export default function Municipales2026() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1
    }
  };

  // Liste des candidats (à remplir au fur et à mesure)
    const CANDIDATE_LISTS = [

    {
      id: 1,
      name: "Liste Kadhafi DJEHAF",
      candidate: "1. M. Kadhafi DJEHAF",
      party: "Divers Droite",
      description: "Une liste engagée pour le renouveau de Mulhouse, portée par une équipe diversifiée.",
      color: "blue",
      members: [
        "2. Mme Houla BENZIDI", "3. M. Matthieu ULUS", "4. Mme Yeliz ULGER", "5. M. Rayane NOUICER", 
        "6. Mme Melanie SCHACHER", "7. M. Feteh SENADLA", "8. Mme Nesma MERIMECH", "9. M. William SCHILL", 
        "10. Mme Sadjia BOUBEKER", "11. M. Jean-Louis SCHNEIDER", "12. Mme Manon LAPIERRE", "13. M. Haci TURGUT", 
        "14. Mme Heba EL ASHREY", "15. M. Savasan SAVASCI", "16. Mme Malika YOUSSEF", "17. M. Gerard HESSE", 
        "18. Mme Corinne SIMONETTI", "19. M. Haci COKUCKUN", "20. Mme Aizhan BEGADILOVA", "21. M. Sarkis ABOU ZEID", 
        "22. Mme Hayad BOUFEDECHE", "23. M. Said SAADI", "24. Mme Sonia LAMOUCHI", "25. M. Elyes HEFAYA", 
        "26. Mme Zohra DAAS", "27. M. Rachid SMOUNI", "28. Mme Nadia BALET", "29. M. Fouad DALILI", 
        "30. Mme Sofia SAYAD", "31. M. Gilles LEBAN", "32. Mme Malika BADRI", "33. M. Nacer BENSLIMANE", 
        "34. Mme Lamia HEFAYA", "35. M. Erkan SIMSEK", "36. Mme Faiza YOUSSEF", "37. M. Abdelhamid BOUDELIOU", 
        "38. Mme Lamia CHEKIERB", "39. M. Brahim BEZAZEL", "40. Mme Djazia YOUSSEF", "41. M. Ali TURGUT", 
        "42. Mme Malika HARKATI", "43. M. Hocine ZERAZA", "44. Mme Bouchra HISSAR", "45. M. Wahib BENSSAM", 
        "46. Mme Selma DEBOUZ", "47. M. Tolga SAVASCI", "48. Mme Marie ABOU ZEID", "49. M. Djamel FALOUTI", 
        "50. Mme Lina ABOU ZEID", "51. M. Sad MEGHRICHE", "52. Mme Lahouaria BEKHEIRA", "53. M. Karim KEBBACI", 
        "54. Mme Neriman CAN", "55. M. Dervis SAVASCI"
      ]
    },
{
      id: 2,
      name: "Liste Christelle RITZ",
      candidate: "1. Mme Christelle RITZ",
      party: "Rassemblement National",
      description: "La liste du Rassemblement National pour Mulhouse.",
      color: "slate",
      members: [
        "2. M. Pierre PINTO", "3. Mme Céline REANT", "4. M. Fabrice CIARLETTA", "5. Mme Laura GIANINO", 
        "6. M. Thierry WUNENBURGER", "7. Mme Jacqueline EBMEYER", "8. M. Alex VANDAELE", "9. Mme Lidia PARLATI", 
        "10. M. Pierre-Hugo BENAÏCHOUCHE", "11. Mme Daciana BAUMANN", "12. M. Abdellah HASNAOUI", "13. Mme Juliette MAURER", 
        "14. M. Romain BARRET", "15. Mme Sabrina SCHMITT", "16. M. Joseph BACHMANN", "17. Mme Sultan BALTA", 
        "18. M. Jean-Pierre CORNUBERT", "19. Mme Magalie DECK", "20. M. Pierre NAEGELIN", "21. Mme Audrey ZISLIN", 
        "22. M. Adam DÖRRBECK", "23. Mme Geneviève ENGLER", "24. M. Francis SOEHNLEN", "25. Mme Anne RUND", 
        "26. M. Bernard MEYER", "27. Mme Corinne PIRANI", "28. M. Florian DEBARD", "29. Mme Fatma BOUGHERARA", 
        "30. M. Philippe LUTZ", "31. Mme Jeanne CHODANOWSKI", "32. M. Olivier BECQUAERT", "33. Mme Suzanne LEONARD", 
        "34. M. Jean-Marie MORGEN", "35. Mme Chantal GRIMONT", "36. M. Michel THÉVENOT", "37. Mme Lucie RINER", 
        "38. M. Dominique LAUNER", "39. Mme Dallila BOLEIRO", "40. M. Davide SCIALPI", "41. Mme Vanessa WILLIG", 
        "42. M. Maurice URBANY", "43. Mme Sophie BRENDER", "44. M. Christian GEAY", "45. Mme Marie-Bernadette MISSLIN", 
        "46. M. Gérard THÉVENOT", "47. Mme Sonia ÖZALP", "48. M. Louis SIMONIN", "49. Mme Marie-Rose SCHMITTLIN", 
        "50. M. Daniel ELIA", "51. Mme Béatrice FERRAND", "52. M. Jacques SOEHNLEN", "53. Mme Liliane SCHLATTER", 
        "54. M. Denis ADLOFF", "55. Mme Michèle PLEUX"
      ]
    },
{
      id: 3,
      name: "Liste Lara MILLION",
      candidate: "1. Mme Lara MILLION",
      party: "Divers centre",
      description: "Une liste centriste proposant une alternative pour la gestion de la ville.",
      color: "emerald",
      members: [
        "2. M. Jean-Lou REICHLING", "3. Mme Anne-Catherine GOETZ", "4. M. Christophe STEGER", "5. Mme Angelique DELAPORTE", 
        "6. M. Jean-Marc AMATRUDA", "7. Mme Kelly PARTOUCHE", "8. M. Philippe LALLEMANT", "9. Mme Catherine CHOPIN", 
        "10. M. Hubert ZUMBIHL", "11. Mme Christine STUDER", "12. M. Philippe D'ORELLI", "13. Mme Peggy MIQUÉE", 
        "14. M. Patrick HELL", "15. Mme Fatoumata SISSOKO", "16. M. Koldoun GARMI", "17. Mme Mireille KUENTZ", 
        "18. M. Mathieu ZUMBIEHL", "19. Mme Aurelia GERBER", "20. M. Virgil WALTER", "21. Mme Dilek KARAKAS", 
        "22. M. Benoit BRAEME", "23. Mme Evelyne KESSLER", "24. M. Maxime DUBS", "25. Mme Corinne MAUDOUX- DE VOLDER", 
        "26. M. Gilles METZ", "27. Mme Marie-Odile SACCHETTI", "28. M. Moustapha DJENAD", "29. Mme Viviane OFFREDI", 
        "30. M. Giuseppe DI BLASI", "31. Mme Nadia BENOUAMER", "32. M. Gilbert BIELLMANN", "33. Mme Sylvie RISS", 
        "34. M. Huseyin KARAMEMIS", "35. Mme Viviane WARTH", "36. M. Jean MENNINGER", "37. Mme Hélène THAI", 
        "38. M. Gökmen TURKMEN", "39. Mme Marie MUSSLIN", "40. M. Gérard SCHAEGIS", "41. Mme Monique LINDACHER", 
        "42. M. Roberto MONTANARO", "43. Mme Evelyne MARTI-NOGUERE", "44. M. Maxence HELFRICH", "45. Mme Catherine BURGART", 
        "46. M. Thomas PERRIER", "47. Mme Charlotte ROBERT", "48. M. Joannes GRENET", "49. Mme Aude DAVID", 
        "50. M. Matteo THILLOY", "51. Mme Alix LEGO", "52. M. Henry SIEGRIST", "53. Mme Régine MISKIEWICZ", 
        "54. M. Bernard HOFFMANN", "55. Mme Brigitte BOUCHEZ"
      ]
    },
{
      id: 4,
      name: "Liste Salah KELTOUMI",
      candidate: "1. M. Salah KELTOUMI",
      party: "Extrême-gauche",
      description: "Une liste engagée pour les travailleurs et la justice sociale.",
      color: "rose",
      members: [
        "2. Mme Nathalie MULOT", "3. M. Pascal NEUSCHWANGER", "4. Mme Chantal BEN NACEUR", "5. M. Romain METEYER", 
        "6. Mme Lison DUCHESNE", "7. M. Philippe SOUCIER", "8. Mme Gwendoline TIRANTE", "9. M. Ryad AOUADHI", 
        "10. Mme Julie GREINER", "11. M. Brice Nel MOUILA", "12. Mme Latifa FARKI RHOZLANI", "13. M. Lorin LOUIS", 
        "14. Mme Christine TEAV", "15. M. Hüseyin TOPRAK", "16. Mme Anne Laure DEFFARGES", "17. M. Landry BERNHEIM", 
        "18. Mme Mériem REBIDJA", "19. M. Étienne CUKIER", "20. Mme Anna-Louise DUROCHER", "21. M. Sidy DIOUF", 
        "22. Mme Pauline CARRÉ", "23. M. Edmond AUBRAS", "24. Mme Géraldine COLLARD", "25. M. Stéphane CARSENTY", 
        "26. Mme Zohra RIAHI", "27. M. Ahmed JALLALI", "28. Mme Honorine BELA ANGO", "29. M. Axel GALAIS", 
        "30. Mme Candice METEYER", "31. M. Julien WOSTYN", "32. Mme Camila ZORZAL PETITPREZ", "33. M. Matthieu SCHNEIDER", 
        "34. Mme Ruhigül KOK", "35. M. Florian DAUTCOURT", "36. Mme Gülüzar DÜMRÜL", "37. M. Pascal RIETH", 
        "38. Mme Fatiha KADDOUR", "39. M. Jordan HERBRICH", "40. Mme Juliette DIGNAT", "41. M. Jaoid EL ARDI", 
        "42. Mme Juliette GUINTREL", "43. M. Djamel ICHALLAL", "44. Mme Marine PÉRIER", "45. M. Younes GHOMRANI", 
        "46. Mme Marie GENEST", "47. M. David BATIGNE", "48. Mme Élie REGAZZONI", "49. M. Feyzullah KOK", 
        "50. Mme Laurence BROXOLLE", "51. M. Youssef SAÏD", "52. Mme Oirda KORICHI", "53. M. Mehdi ALOUACHE", 
        "54. Mme Émilie BARRAL", "55. M. Géraud FERRY"
      ]
    },
{
      id: 5,
      name: "Liste Michèle LUTZ",
      candidate: "1. Mme Michèle LUTZ",
      party: "Divers droite",
      description: "La liste de la majorité municipale sortante pour poursuivre le développement de Mulhouse.",
      color: "indigo",
      members: [
        "2. M. Alain COUCHOT", "3. Mme Marie HOTTINGER", "4. M. Florian COLOM", "5. Mme Aya HIMER", 
        "6. M. Antoine LINARES", "7. Mme Marie CORNEILLE", "8. M. Julien DEMAËL", "9. Mme Laure HOUIN", 
        "10. M. Florent WURTH", "11. Mme Claudine BONI DA SILVA", "12. M. Thierry NICOLAS", "13. Mme Fatima JENN", 
        "14. Henri METZGER", "15. Mme Séverine LIBOLD", "16. M. Ayoub BILA", "17. Mme Emmanuelle SUAREZ", 
        "18. M. Beytullah BEYAZ", "19. Mme Christelle DI MARCO", "20. M. Alfred JUNG", "21. Mme Corinne LOISEL", 
        "22. M. Jean-Yves CAUSER", "23. Mme Célia KASSI", "24. M. Pascal WITTMANN", "25. Mme Saadia ZAGAOUI", 
        "26. M. Jean-Claude CHAPATTE", "27. Mme Sandra MULLER", "28. M. Arthur HILBRUNNER", "29. Mme Nour BOUAMAIED", 
        "30. M. Tom CARDOSO", "31. Mme Laurence BRUNOT", "32. M. Pascal COINCHELIN", "33. Mme Virginie RAPIN", 
        "34. M. Hasan BINICI", "35. Mme Liliane KOSIR", "36. M. Thierry MILHAU", "37. Mme Géraldine ESPIN", 
        "38. M. Mamadou BARRY", "39. Mme Martine BOUDAUD", "40. M. Gilles WEISZROCK", "41. Mme Anne-Sophie POIRÉ", 
        "42. M. Vincent NIVLET", "43. Mme Catherine DIETSCH", "44. M. Fawdi KABAB", "45. Mme Mary-Estelle NGUYEN", 
        "46. M. Cameron TOUATI", "47. Mme Léa BURGY", "48. M. Adam LIMAM", "49. Mme Martine FOREST", 
        "50. M. Yves ANCEL", "51. Mme Armelle GIROUD", "52. M. Philippe WESPISER", "53. Mme Rose-Marie DURRWELL", 
        "54. M. Marc SCHITTLY", "55. Mme Catherine RAPP"
      ]
    },
{
      id: 6,
      name: "Liste Annouar SASSI",
      candidate: "1. M. Annouar SASSI",
      party: "Divers",
      description: "Une liste indépendante proposant une nouvelle vision pour Mulhouse.",
      color: "orange",
      members: [
        "2. Mme Patricia LEGOUGE", "3. M. Thibault BENABID", "4. Mme Sirine BEN HADJ", "5. M. Soheib HADDAD", 
        "6. Mme Isabelle MAURER", "7. M. Mohamed ACHBAKH", "8. Mme Kadiatou GUEYE", "9. M. Gilles DIETERLEN", 
        "10. Mme Florence FAIVRE", "11. M. Ayhan CIPLAK", "12. Mme Caroline ADLI", "13. M. Cyrille CRETIEN", 
        "14. Mme Lilia MESSSIAD", "15. M. Ahmed HADDAD", "16. Mme Fadwa DAHAR", "17. M. Anderson LEWIS-ROCHA", 
        "18. Mme Solène HUCHET", "19. M. Detlef SCHULMANN", "20. Mme Bouchra BINCKLI", "21. M. Azhar BENHAIDA", 
        "22. Mme Rannia MEGROUH", "23. M. Gilles MARTIN", "24. Mme Leonisa MAZREKAJ", "25. M. Francois ROCH", 
        "26. Mme Deborah KELLER", "27. M. Ahmed Imed SID", "28. Mme Jamila DIOUANE", "29. M. Vincent PICARD", 
        "30. Mme Sophie CAMATTE", "31. M. Florent BINCKLI", "32. Mme Sabah DJEKRIF", "33. M. Pierre MAILLARD", 
        "34. Mme Christelle BADER", "35. M. Melvil SCHULMANN", "36. Mme Géraldine SCHURDER", "37. M. Mohamed IDRISSI LAHLOU", 
        "38. Mme Kenza NASSAIBIA REDJALA", "39. M. Sebastien SAIHI", "40. Mme Zaynab TAHIR", "41. M. Fidèle DAO", 
        "42. Mme Cylia KELLER", "43. M. Renaud PORTE", "44. Mme Mélody OURDOUILLIE", "45. M. Didier Emilio BOSCARI", 
        "46. Mme Pauline CUTULI", "47. M. Michel TUFUTA-LULENDI", "48. Mme Delphine WAGNER", "49. M. Martin MUZET", 
        "50. Mme Aysel CITAK", "51. M. Samir TOUTAOUI", "52. Mme Christiane SCHWEYER", "53. M. Michael Philippe GIRARD", 
        "54. Mme Sylvie BIROT", "55. M. Serge BERTELLI"
      ]
    },
{
      id: 7,
      name: "Liste Eliot GAFANESCH",
      candidate: "1. M. Eliot GAFANESCH",
      party: "La France insoumise",
      description: "Une liste portant le programme de l'Union Populaire pour Mulhouse.",
      color: "red",
      members: [
        "2. Mme Fathia LAMA", "3. M. Arthur MILON", "4. Mme Lilia SAHLOUN", "5. M. Djamal OSMANI", 
        "6. Mme Eve GAUTIER", "7. M. Emmanuel GAUTIER", "8. Mme Simone FEST", "9. M. Maxime RUNZER", 
        "10. Mme Ursula CHENU", "11. M. Loïck GIRARD", "12. Mme Yasmina BOUTTINE", "13. M. Arnaud CARDON", 
        "14. Mme Sandra THIOUX", "15. M. Gwen MESSE", "16. Mme Lilah LANDAIS", "17. M. Yaya KHEFFI", 
        "18. Mme Leone BOUKRAA", "19. M. Michael HABIB", "20. Mme Nesrine OSMANI", "21. M. Loic PAPIRER", 
        "22. Mme Joanna DUCLAP", "23. M. Morit LABROUMANI", "24. Mme Laurianne FLESCH", "25. M. Paul Aime HOHWALD", 
        "26. Mme Leo LALLEMAND-LAVOIPIERE", "27. M. Paul SCHELCHER", "28. Mme Samara SOLTANI", "29. M. Thierry MOINE", 
        "30. Mme Annie PASTOR", "31. M. Paul PIERQUIN", "32. Mme Alice BRUC", "33. M. Luca COLARELLI", 
        "34. Mme Françoise ORCEL", "35. M. Iain SCHELCHER", "36. Mme Ilhem LITIM", "37. M. Pierre TALPAERT", 
        "38. Mme Claudine GAMBINO", "39. M. Valentin FELS", "40. Mme Samia HADJI", "41. M. Michel BURKHARD", 
        "42. Mme Marie WEISSER", "43. M. Matheo JEANPIERRE", "44. Mme Alice WINLING", "45. M. Michel BOUANAKA", 
        "46. Mme Agathe SIFFERT", "47. M. François HEITZ", "48. Mme Anne BALDENSPERGER", "49. M. Sylvain LEJEUNE", 
        "50. Mme Josette LABOUR", "51. M. Salah MAALEM", "52. Mme Anne WEINSTOERFFER", "53. M. Lucas MATIAS", 
        "54. Mme Amandine TOFFALONI", "55. M. Charlie SEBBANE"
      ]
    },
{
      id: 8,
      name: "Liste Emmanuel TAFFARELLI",
      candidate: "1. M. Emmanuel TAFFARELLI",
      party: "Reconquête !",
      description: "La liste de Reconquête ! pour défendre l'identité et la sécurité à Mulhouse.",
      color: "sky",
      members: [
        "2. Mme Gwendoline Annabelle HECK-BILGER", "3. M. Antony THOMA", "4. Mme Rachel BOULAIRE", "5. M. Patrick DUFLOT", 
        "6. Mme Déborah PORHANSL", "7. M. Victor OLRY", "8. Mme Maria Luiza SCHNEIDER", "9. M. Sylvain MULLER", 
        "10. Mme Francine KOLAR", "11. M. Jordan HECK", "12. Mme Sylvie FROEHLY", "13. M. Camille RENNER", 
        "14. Mme Frédérique FROEHLY", "15. M. Jacques ARKOUB", "16. Mme Madeleine HERZOG", "17. M. Marc LAZERT", 
        "18. Mme Danielle GAERTNER", "19. M. Julien HERNANDEZ", "20. Mme Zélia DA COSTA REZENDE", "21. M. Frédéric AUER", 
        "22. Mme Claude GEBEL", "23. M. Roberto QUARTERONI", "24. Mme Michèle KIENTZ", "25. M. Etienne VONESCH", 
        "26. Mme Irène PETEL", "27. M. Olivier PHILIPPOT", "28. Mme Samia ELKERIA", "29. M. Christophe RISSER", 
        "30. Mme Alice RIO", "31. M. Bernard RUNSER", "32. Mme Bintou SISSOKO", "33. M. Jean-Louis TOCHTERMANN", 
        "34. Mme Marguerite NOLET", "35. M. Adrien THIERY", "36. Mme Angélique HUMMEL", "37. M. Stéphane TORT", 
        "38. Mme Denise RIFF", "39. M. Hermann BROBECKER", "40. Mme Brigitte BATTAGLIA", "41. M. Florian WOIRY", 
        "42. Mme Sylvie WERNER", "43. M. Raymond KIRCHHOFF", "44. Mme Mireille TOURNE", "45. M. Maxime ROUZIES", 
        "46. Mme Aimée DIRINGER", "47. M. Florent GLIN", "48. Mme Elsa BOIGUES", "49. M. Gilbert KLING", 
        "50. Mme Lina MELONI", "51. M. Paul DUPORT", "52. Mme Evelyne ROHMER", "53. M. Alexis ABENZOAR", 
        "54. Mme Claire FOUCHARD", "55. M. Charles-Antoine BINDER"
      ]
    },
{
      id: 9,
      name: "Liste Cécile SORNIN",
      candidate: "1. Mme Cécile SORNIN",
      party: "Divers centre",
      description: "Une liste centriste engagée pour la proximité et l'innovation à Mulhouse.",
      color: "teal",
      members: [
        "2. M. Lionel L'HARIDON", "3. Mme Nadia FAVROT", "4. M. Oualid BEN SALEM", "5. Mme Nathalie KREUTTER", 
        "6. M. Alfred OBERLIN", "7. Mme Houria CHIBOUT", "8. M. Pierre-Yves GUILLOT", "9. Mme Sylvie COURANT", 
        "10. M. Eric HUMBERT", "11. Mme Manuella NGNAFEU", "12. M. Alexis HAMEL", "13. Mme Souad GRINE", 
        "14. M. Tidiane DIA", "15. Mme Valérie PUECH", "16. M. Marc WILLIG", "17. Mme Zeynep YILDIZ", 
        "18. M. Mourad BRIHI", "19. Mme Sounia CHERAITA", "20. M. Claude FAVROT", "21. Mme Isabelle FAESSEL", 
        "22. M. Jean RUCH", "23. Mme Myriam BOUKHECHEM", "24. M. Bernard STOESSEL", "25. Mme Chelsea HAYES", 
        "26. M. Thomas GOUTTE", "27. Mme Zaya MERIMECHE", "28. M. Stéphane METZGER", "29. Mme Joanne BOULANGER", 
        "30. M. Nicolas THIERY", "31. Mme Ouarda AGHBAL", "32. M. Thierry GRELL", "33. Mme Mare NDIAYE", 
        "34. M. Jean-Marie GUTZWILLER", "35. Mme Fatima DAHMOUNI", "36. M. Frédéric MALACZYNSKI", "37. Mme Linda GUEHAMA", 
        "38. M. Djelloul AISSAOUI", "39. Mme Emine SEN", "40. M. Michel MILFORT", "41. Mme Anne Cécile JOORIS", 
        "42. M. Olivier VANDEMEULEBROUCKE", "43. Mme Amel MOKHNACHI", "44. M. Kader BOUZANA", "45. Mme Marie Paule TIXIER", 
        "46. M. Gilbert SOLIGO", "47. Mme Johanna WEAVER", "48. M. Nicolas KHATTAB", "49. Mme Daniele Alice BAGARD", 
        "50. M. Franco IANNONE", "51. Mme Jacqueline BROUG", "52. M. Philippe ALTMAYER", "53. Mme Françoise DIETERICH", 
        "54. M. Denis RAMBAUD", "55. Mme Dolores VENTOROSI"
      ]
    },
{
      id: 10,
      name: "Liste Frédéric MARQUET",
      candidate: "1. M. Frédéric MARQUET",
      party: "Divers centre",
      description: "Une liste centriste proposant une nouvelle dynamique commerciale et citoyenne.",
      color: "cyan",
      members: [
        "2. Mme Carine DE MARIN", "3. M. Rodolphe CAHN", "4. Mme Anne LAUMOND", "5. M. Frédéric GUTHMANN", 
        "6. Mme Delphine GHELLI", "7. M. Boubaker FETTIS", "8. Mme Valérie DERENDINGER", "9. M. Robert SOUSSAN", 
        "10. Mme Sarah ZEHRI", "11. M. Denis PAULIAC", "12. Mme Delphine EHRBURGER", "13. M. Francis GRIENENBERGER", 
        "14. Mme Julia MOTA-ANTONI", "15. M. Thierry COUTAYE", "16. Mme Brigitte Biriçik SACARD", "17. M. Philippe DUVERNOIS", 
        "18. Mme Mélanie MARCHANT", "19. M. Arnaud BUCHER", "20. Mme Maïté RUGIERO", "21. M. Rémy BURGY", 
        "22. Mme Laurielle SOSSAH", "23. M. Michel WIEDERKEHR", "24. Mme Malvine FREY", "25. M. Olivier ERHARD", 
        "26. Mme Karine GARCIA-FERNANDEZ", "27. M. Laurent BRAUMANN", "28. Mme Aude BRUNO-SISSELIN", "29. M. Alessandro RIGONI", 
        "30. Mme Nathalie FRANCIS", "31. M. Philippe FICHTER", "32. Mme Naoual LAKHDAR", "33. M. Frédéric BECK", 
        "34. Mme Florence PARYS", "35. M. Michael KUNTZ", "36. Mme Margaux DELCOURT", "37. M. Alexandre MAAMAR", 
        "38. Mme Daria BAIANDOUROVA-KETTERLIN", "39. M. Lucas LORENZI", "40. Mme Sarah ALAVI", "41. M. Nicolas ROHMER", 
        "42. Mme Géraldine ZETTEL", "43. M. Manuel FIX", "44. Mme Isabelle BULLIOT", "45. M. Kostadin GEORGIEV", 
        "46. Mme Céline BOURGEOIS", "47. M. Claude PILLON", "48. Mme Hanen MEKNI", "49. M. Fabien SCHNOEBELEN", 
        "50. Mme Clara ALLEGRETTI", "51. M. Emmanuel GARCIA-FERNANDEZ", "52. Mme Dominique WINTZENRIETH", "53. M. Benjamin MIERZWIAK", 
        "54. Mme Sabine SCHNABEL", "55. M. David BALL", "56. Mme Agnès GROSS", "57. M. Yves KETTLER"
      ]
    },
{
      id: 11,
      name: "Liste Loïc MINERY",
      candidate: "1. M. Loïc MINERY",
      party: "Union à gauche",
      description: "La liste de rassemblement des forces de gauche et d'écologie pour Mulhouse.",
      color: "purple",
      members: [
        "2. Mme Pascale Cléo SCHWEITZER", "3. M. Joseph SIMEONI", "4. Mme Fatiha GUEMAZI-KHEFFI", "5. M. Thiébaut WEBER", 
        "6. Mme Léonie HEBERT", "7. M. Jonas CARDOSO", "8. Mme Nadia EL HAJJAJI", "9. M. Salim BIROUK", 
        "10. Mme Sabrina BOUZIDI", "11. M. Éric ALARIO", "12. Mme Maréva BUNGA-CHIRON", "13. M. Jonathan SEILLER", 
        "14. Mme Carole ECOFFET", "15. M. Philippe SCHWEYER", "16. Mme Siam Angie GUYOT", "17. M. Boris ANGER", 
        "18. Mme Magda DAUDIN", "19. M. Jordan GEIN", "20. Mme Josiane WALTER", "21. M. Jean WILLMÉ", 
        "22. Mme Pia GERZMANN", "23. M. Paul-André STRIFFLER", "24. Mme Hafida DEROUICHE", "25. M. Benjamin BUCHET", 
        "26. Mme Greshmi VARAPIRAGASAM", "27. M. Jonathan KOHLER", "28. Mme Lobna CHARNI", "29. M. Amadou SOW", 
        "30. Mme Anaïs SCHLIENGER", "31. M. David DOLUI", "32. Mme Merve ERDOGAN", "33. M. Romaric GARNIER", 
        "34. Mme Nathalie DUBIÉ", "35. M. Bernard GREEN", "36. Mme Lina MAHDIYAN", "37. M. Alban BRUA", 
        "38. Mme Nadia SAOU", "39. M. Elliot THIERRY", "40. Mme Ghislaine UMHAUER", "41. M. Florian CAVODEAU", 
        "42. Mme Juliette KRANZ", "43. M. Hasan YAKISAN", "44. Mme Laure CESCUTTI", "45. M. Jacques HORRENBERGER", 
        "46. Mme Christelle MOKENGO BONKOSSI", "47. M. Laurent SCHNEIDER", "48. Mme Anne-Marie LEVASSORT", "49. M. Jean-Pierre VALENTIN", 
        "50. Mme Lydie PLOUX", "51. M. Emir VURAL", "52. Mme Chantal LESER", "53. M. Denis WIESSER", 
        "54. Mme Agnès TOPOUZIAN-SCHNEIDER", "55. M. Pierre FREYBURGER", "56. Mme Emmanuelle WATTRELOS"
      ]
    }
  
  ];

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
      {/* Header / Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Link 
                href="/"
                className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-slate-600 dark:text-slate-400"
              >
                <ChevronLeft size={24} />
              </Link>
              <div className="flex items-center gap-2">
                <Logo />
                <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
                  Municipales 2026
                </span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-16"
        >
          {/* Hero Section */}
          <motion.div variants={itemVariants} className="text-center space-y-6 max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium text-sm mb-4">
              <Vote size={18} />
              <span>Dossier Spécial Élections</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight">
              L&apos;avenir de Mulhouse se joue en 2026
            </h1>
            <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 leading-relaxed">
              Suivez en direct toute l&apos;actualité, les candidats, les programmes et les enjeux du scrutin municipal à Mulhouse.
            </p>
          </motion.div>

          {/* CANDIDATES GRID SECTION */}
          {CANDIDATE_LISTS.length > 0 && (
            <motion.section variants={itemVariants} className="space-y-8">
              <div className="flex items-center gap-3">
                <div className="h-8 w-1.5 bg-blue-600 rounded-full"></div>
                <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Les Listes Candidates</h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {CANDIDATE_LISTS.map((list) => (
                  <motion.div 
                    key={list.id}
                    whileHover={{ y: -5 }}
                    className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col"
                  >
                    <div className={`h-2 w-full bg-${list.color || 'blue'}-500`}></div>
                    <div className="p-6 space-y-4 flex-grow">
                      <div className="space-y-1">
                        <span className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                          {list.party}
                        </span>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white leading-snug">
                          {list.name}
                        </h3>
                      </div>
                      
                      <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                        <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-slate-500">
                          <Users size={20} />
                        </div>
                        <div>
                          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Tête de liste</p>
                          <p className="font-bold text-slate-900 dark:text-white">{list.candidate}</p>
                        </div>
                      </div>
                      
                      <p className="text-slate-600 dark:text-slate-400 text-sm italic leading-relaxed">
                        &quot;{list.description}&quot;
                      </p>
                    </div>
                    
                    <div className="p-4 bg-slate-50 dark:bg-slate-800/30 border-t border-slate-100 dark:border-slate-800">
                      <button className="w-full py-2 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                        Voir le programme →
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.section>
          )}

          {/* Status Alert */}
          <motion.div variants={itemVariants} className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-2xl p-6 flex flex-col md:flex-row items-center gap-6 max-w-4xl mx-auto">
            <div className="p-4 bg-amber-100 dark:bg-amber-900/40 rounded-xl text-amber-600 dark:text-amber-400">
              <Info size={32} />
            </div>
            <div className="text-center md:text-left space-y-2">
              <h3 className="text-xl font-bold text-amber-900 dark:text-amber-100">Dossier en cours de préparation</h3>
              <p className="text-amber-800/80 dark:text-amber-200/80">
                Nos équipes préparent un suivi complet pour les élections municipales de 2026. 
                Revenez prochainement pour découvrir les premières analyses et les profils des candidats.
              </p>
            </div>
          </motion.div>

          {/* Grid of future sections */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-8">
            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-xl transition-all duration-300 group">
              <div className="w-14 h-14 bg-indigo-100 dark:bg-indigo-900/30 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-6 group-hover:scale-110 transition-transform">
                <Users size={28} />
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3">Candidats & Listes</h3>
              <p className="text-slate-600 dark:text-slate-400">
                Retrouvez les portraits détaillés de chaque candidat et la composition des différentes listes engagées.
              </p>
            </motion.div>

            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-xl transition-all duration-300 group">
              <div className="w-14 h-14 bg-emerald-100 dark:bg-emerald-900/30 rounded-2xl flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-6 group-hover:scale-110 transition-transform">
                <Calendar size={28} />
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3">Agenda & Débats</h3>
              <p className="text-slate-600 dark:text-slate-400">
                Ne manquez aucune date clé : réunions publiques, débats télévisés et moments forts de la campagne.
              </p>
            </motion.div>

            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-xl transition-all duration-300 group">
              <div className="w-14 h-14 bg-rose-100 dark:bg-rose-900/30 rounded-2xl flex items-center justify-center text-rose-600 dark:text-rose-400 mb-6 group-hover:scale-110 transition-transform">
                <MessageSquare size={28} />
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3">Enquêtes & Analyses</h3>
              <p className="text-slate-600 dark:text-slate-400">
                Décryptage des enjeux locaux, sondages et analyse des programmes par notre rédaction.
              </p>
            </motion.div>
          </div>

          {/* Footer note */}
          <motion.div variants={itemVariants} className="text-center pt-12 border-t border-slate-200 dark:border-slate-800">
            <p className="text-slate-500 dark:text-slate-500 text-sm">
              © 2026 Mulhouse Actu - Spécial Élections Municipales. Tous droits réservés.
            </p>
          </motion.div>
        </motion.div>
      </div>
    </main>
  );
}
