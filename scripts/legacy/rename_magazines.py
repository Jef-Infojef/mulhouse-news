import os

folder = "M+Mag"
mapping = {
    "MM15.pdf": "mars-avril-mai 2021",
    "MM16.pdf": "juillet-août-septembre 2021",
    "MM17.pdf": "octobre-novembre-décembre 2021",
    "MM18.pdf": "décembre 2021",
    "MM19.pdf": "avril-mai-juin 2022",
    "MM20.pdf": "juillet-août-septembre 2022",
    "MM21.pdf": "octobre-novembre-décembre 2022",
    "MM22.pdf": "décembre 2022",
    "MM23.pdf": "printemps 2023",
    "MM24.pdf": "été 2023",
    "MM25.pdf": "automne 2023",
    "MM26.pdf": "hiver 2023",
    "MM27.pdf": "printemps 2024",
    "MM28.pdf": "été 2024",
    "MM29.pdf": "automne 2024",
    "MM30.pdf": "hiver 2024",
    "MM31.pdf": "printemps 2025",
    "MM32.pdf": "été 2025",
    "MM33.pdf": "automne 2025",
    "MM34.pdf": "hiver 2025"
}

for old_name, date_str in mapping.items():
    old_path = os.path.join(folder, old_name)
    if os.path.exists(old_path):
        # Format : M_Mag_XX_Date.pdf
        num = old_name.replace("MM", "").replace(".pdf", "")
        new_name = f"M_Mag_{num}_{date_str.replace(' ', '_').replace('/', '-')}.pdf"
        new_path = os.path.join(folder, new_name)
        print(f"Renaming {old_name} -> {new_name}")
        os.rename(old_path, new_path)
