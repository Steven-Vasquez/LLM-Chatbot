import random, sys

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


from sql_connection import get_db_connection

conn = get_db_connection()
if not conn:
    raise Exception("Failed to connect to SQL Server")
c = conn.cursor()

makes = {
    "Honda": ["Civic", "Accord"],
    "Toyota": ["Camry", "Corolla"],
    "Ford": ["F-150", "Focus"]
}

trims = ["Base", "Sport", "EX", "LX", "Touring"]
engines = ["2.0L", "2.4L", "1.8L", "3.5L"]

# Insert vehicles
for make, models in makes.items():
    for model in models:
        for year in range(2015, 2023):
            for trim in trims:
                for engine in engines:
                    c.execute(
                        "INSERT INTO vehicles (make, model, year, trim, engine) VALUES (?,?,?,?,?)",
                        (make, model, year, trim, engine)
                    )

# Insert parts
for i in range(1, 200):
    c.execute(
        "INSERT INTO parts (part_number, name, category) VALUES (?,?,?)",
        (f"P{i:04}", f"Brake Rotor {i}", "Brakes")
    )

# Insert fitment rules
for part_id in range(1, 200):
    make = random.choice(list(makes.keys()))
    model = random.choice(makes[make])
    start = random.randint(2015, 2018)
    end = random.randint(2019, 2022)
    trim = random.choice(trims)
    engine = random.choice(engines)

    c.execute("""
        INSERT INTO part_fitment
        (part_id, make, model, year_start, year_end, trim, engine, notes)
        VALUES (?,?,?,?,?,?,?,?)
    """, (part_id, make, model, start, end, trim, engine, "OEM compatible"))

conn.commit()
conn.close()
