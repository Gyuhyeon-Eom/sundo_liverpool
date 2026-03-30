import json

# Read notebook
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Cell 7.5 (환승 거점 선정) - search by section comment
target_cell_idx = None
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if '# 7.5 주요 환승 거점 선정 (시작점/종점 후보)' in source and 'major_hubs.head(15)' in source:
            # 두 번째 발견된 것을 사용 (첫 번째는 이전 버전)
            if target_cell_idx is not None:
                target_cell_idx = i
                break
            target_cell_idx = i

if target_cell_idx is None:
    print("Cell 7.5를 찾을 수 없습니다.")
    # 대신 마지막으로 발견된 것 사용
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if '# 7.5 주요 환승 거점' in source:
                target_cell_idx = i

if target_cell_idx is None:
    print("Cell 7.5를 찾을 수 없습니다.")
    exit(1)

# New code for Cell 7.5 with direct coordinate mapping from bus_routes
new_code = """# 7.5 주요 환승 거점 선정 (시작점/종점 후보)

# 지하철역만 필터링 (심야 승차량 상위)
subway_stations = night_station[night_station['station_name'].str.contains('지하철', na=False)].copy()
major_hubs = subway_stations.nlargest(15, '심야승차량')

print(f'=== 주요 심야 환승 거점 (Top 15) ===')
print(major_hubs[['station_name', '심야승차량']])

# 좌표 매핑: bus_routes에서 역명으로 찾기
hub_coords = major_hubs.copy()
hub_coords['GPS_X'] = None
hub_coords['GPX_Y'] = None

for idx, hub in hub_coords.iterrows():
    station_name = hub['station_name']

    # "지하철" 제거하고 매칭
    station_clean = station_name.replace('지하철', '').strip()

    # bus_routes에서 정류소명에 역명이 포함된 것 찾기
    matching = bus_routes[bus_routes['정류소명'].str.contains(station_clean, na=False, regex=False)]

    if len(matching) > 0:
        # 가장 많이 등장하는 좌표 사용
        coords_group = matching.groupby(['GPS_X', 'GPX_Y']).size().reset_index(name='count')
        coords_group = coords_group.sort_values('count', ascending=False)

        hub_coords.at[idx, 'GPS_X'] = coords_group.iloc[0]['GPS_X']
        hub_coords.at[idx, 'GPX_Y'] = coords_group.iloc[0]['GPX_Y']

matched = hub_coords['GPS_X'].notna().sum()
print(f'\\n좌표 매핑 결과: {matched}/{len(hub_coords)}')

if matched < 10:
    print('\\n경고: 10개 미만의 환승거점만 좌표가 매핑되었습니다.')
    print('매핑 실패한 거점:')
    print(hub_coords[hub_coords['GPS_X'].isna()][['station_name', '심야승차량']])
else:
    print(f'✓ {matched}개 환승 거점 좌표 매핑 완료')

# GeoDataFrame 생성 (좌표가 있는 것만)
hub_gdf = hub_coords[hub_coords['GPS_X'].notna()].copy()
hub_gdf = gpd.GeoDataFrame(
    hub_gdf,
    geometry=[Point(row['GPS_X'], row['GPX_Y']) for _, row in hub_gdf.iterrows()],
    crs='EPSG:4326'
).to_crs('EPSG:5179')

print(f'환승 거점 GeoDataFrame 생성: {len(hub_gdf)}개')
"""

# Update cell
nb['cells'][target_cell_idx]['source'] = new_code.split('\n')
nb['cells'][target_cell_idx]['outputs'] = []
nb['cells'][target_cell_idx]['execution_count'] = None

# Write back
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Cell 7.5 수정 완료 (cell index={target_cell_idx})")
print("환승 거점 좌표 매핑을 bus_routes 기반으로 수정했습니다.")
