import duckdb

db_path = r"d:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\data_integration2.duckdb"
con = duckdb.connect(db_path)

try:
    print("Testing CREATE TABLE with FK...")
    con.execute("CREATE TABLE IF NOT EXISTS test_dim (id INT PRIMARY KEY)")
    con.execute("CREATE TABLE IF NOT EXISTS test_fact (id INT, dim_id INT, FOREIGN KEY (dim_id) REFERENCES test_dim(id))")
    print("CREATE TABLE with FK succeeded.")
    
    # Verify constraint
    constraints = con.execute("SELECT * FROM duckdb_constraints WHERE table_name='test_fact'").fetchall()
    print("Constraints found:", constraints)
    
    con.execute("DROP TABLE test_fact")
    con.execute("DROP TABLE test_dim")
    
except Exception as e:
    print(f"CREATE TABLE check failed: {e}")

con.close()

