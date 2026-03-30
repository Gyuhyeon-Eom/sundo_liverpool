import json

# Read notebook
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find cell with night_boarding error
target_idx = None

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if '심야 수단별 노선 이용 현황' in source and 'night_boarding' in source:
            target_idx = i
            break

if target_idx is None:
    print("Cell 5-2.3을 찾을 수 없습니다.")
    exit(1)

# New code using night_df and filtering for boarding only
new_code = """# 5-2.3 심야 수단별 노선 이용 현황

# 승차만 필터링
night_boarding = night_df[night_df['in_out'].str.startswith('0')].copy()

night_routes = night_boarding.groupby(['transport_name', 'transport_id']).size().reset_index(name='심야승차량')
night_routes = night_routes.sort_values('심야승차량', ascending=False)

print(f'=== 심야 노선별 승차량 상위 20 ===')
print(night_routes.head(20).to_string(index=False))

# 심야 운행 노선 수
print(f'\\n심야 이용 노선 수: {night_routes["transport_id"].nunique()}')
print(f'심야버스(이름에 심야 포함): {night_routes[night_routes["transport_name"].str.contains("심야", na=False)]["transport_id"].nunique()}개')
"""

# Update cell
nb['cells'][target_idx]['source'] = new_code.split('\n')
nb['cells'][target_idx]['outputs'] = []
nb['cells'][target_idx]['execution_count'] = None

# Write back
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Cell 5-2.3 (index={target_idx}) 수정 완료")
print("night_df에서 승차만 필터링하여 night_boarding 생성")
