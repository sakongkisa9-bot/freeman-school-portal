import sqlite3

conn = sqlite3.connect('freeman_data.db')
cursor = conn.cursor()

# Get a sample row from marksheet
print('Sample row from marksheet:')
cursor.execute('SELECT * FROM marksheet LIMIT 1')
result = cursor.fetchone()
if result:
    print(f"  adm_no: {result[0]}")
    print(f"  total_points: {result[1]}")
    print(f"  average_points: {result[2]}")
    print(f"  rank: {result[3]}")
    print(f"  math_s: {result[4]}, math_r: {result[5]}, math_p: {result[6]}")
    print(f"  eng_s: {result[7]}, eng_r: {result[8]}, eng_p: {result[9]}")
    print(f"  kisw_s: {result[10]}, kisw_r: {result[11]}, kisw_p: {result[12]}")
    print(f"  int_scie_s: {result[13]}, int_scie_r: {result[14]}, int_scie_p: {result[15]}")
    print(f"  pre_tech_s: {result[16]}, pre_tech_r: {result[17]}, pre_tech_p: {result[18]}")
    print(f"  sst_s: {result[19]}, sst_r: {result[20]}, sst_p: {result[21]}")
    print(f"  cre_s: {result[22]}, cre_r: {result[23]}, cre_p: {result[24]}")
    print(f"  agri_s: {result[25]}, agri_r: {result[26]}, agri_p: {result[27]}")
    print(f"  c_a_s: {result[28]}, c_a_r: {result[29]}, c_a_p: {result[30]}")
else:
    print('  No data found in marksheet')

conn.close()
