import json

# Read notebook
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Cell 4.3 (정차 노선 수)
target_idx = None

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if '# 4.3 정차 노선 수 (집계구 단위)' in source and 'routes_per_stop' in source:
            target_idx = i
            break

if target_idx is None:
    print("Cell 4.3을 찾을 수 없습니다.")
    exit(1)

# New code with name-based matching
new_code = """# 4.3 정차 노선 수 (집계구 단위)

# 정류소명 기준으로 bus_routes와 bus_stops_shp 매칭
stops_routes = bus_stops_shp[['bstopid', 'geometry', 'bstopnm_clean']].copy()

# 정류소별 노선 수 계산 (정류소명 기준)
routes_per_stop = bus_routes.groupby('정류소명_clean')['노선번호'].nunique().reset_index()
routes_per_stop.columns = ['정류소명_clean', '정차노선수']

# 정류소명으로 매칭
stops_routes = stops_routes.merge(routes_per_stop, on='정류소명_clean', how='left')
stops_routes['정차노선수'] = stops_routes['정차노선수'].fillna(0).astype(int)

print(f'정차노선수 매핑: {(stops_routes["정차노선수"] > 0).sum()}/{len(stops_routes)}개 정류소')

# 집계구와 공간 조인 후 정차노선수 집계
stops_in_census2 = gpd.sjoin(stops_routes, census, how='inner', predicate='within')

# 집계구별 총 정차노선수 (중복 제거)
routes_per_census = stops_in_census2.groupby('TOT_REG_CD')['정차노선수'].sum().reset_index()
routes_per_census.columns = ['TOT_REG_CD', '총정차노선수']

census_with_stops = census_with_stops.merge(routes_per_census, on='TOT_REG_CD', how='left')
census_with_stops['총정차노선수'] = census_with_stops['총정차노선수'].fillna(0).astype(int)

print('=== 정차 노선 수 (집계구 단위) ===')
print(census_with_stops['총정차노선수'].describe())

print(f'\\n정차노선수 상위 10 집계구:')
top_routes = census_with_stops.nlargest(10, '총정차노선수')[['TOT_REG_CD', '정류소수', '총정차노선수']]
print(top_routes.to_string(index=False))
"""

# Update cell
nb['cells'][target_idx]['source'] = new_code.split('\n')
nb['cells'][target_idx]['outputs'] = []
nb['cells'][target_idx]['execution_count'] = None

# Write back
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Cell 4.3 (index={target_idx}) 수정 완료")
print("변경 내용: 정류소ID 매칭 → 정류소명 매칭으로 변경")
