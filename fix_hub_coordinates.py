import json

# Read notebook
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Cell 7.5 (환승 거점 선정)
target_cell_idx = None
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if '# 7.5 주요 환승 거점 선정' in source and 'major_hubs.head(15)' in source:
            target_cell_idx = i
            break

if target_cell_idx is None:
    print("Cell 7.5를 찾을 수 없습니다.")
    exit(1)

# New code for Cell 7.5 with direct subway station coordinate mapping
new_code = """# 7.5 주요 환승 거점 선정 (심야 승차량 상위 15개 지하철역)

# 지하철역만 필터링 (심야 승차량 상위)
subway_stations = night_station[night_station['station_name'].str.contains('지하철', na=False)].copy()
major_hubs = subway_stations.nlargest(15, '심야승차량')

print(f'=== 주요 심야 환승 거점 (Top 15) ===')
print(major_hubs[['station_name', '심야승차량']])

# station_id를 문자열로 변환
major_hubs_clean = major_hubs.copy()
major_hubs_clean['station_id_str'] = major_hubs_clean['station_id'].astype(str).str.zfill(7)
major_hubs_clean['station_name_clean'] = major_hubs_clean['station_name'].str.strip()

# 지하철역 좌표를 card 데이터에서 직접 찾기 (지하철 거래만)
subway_card = card[card['수단'] == '지하철'].copy()

# station_id 매칭을 위해 정리
subway_card['station_id_str'] = subway_card['station_id'].astype(str).str.zfill(7)

# 각 환승거점에 대해 좌표 찾기
hub_coords = major_hubs_clean.copy()
hub_coords['GPS_X'] = None
hub_coords['GPX_Y'] = None

# 지하철 승차 데이터에서 station_id별 GPS 좌표 추출
for idx, hub in hub_coords.iterrows():
    station_id = hub['station_id_str']

    # 해당 역의 승차 기록 찾기 (in_out이 0으로 시작하는 승차 기록)
    station_records = subway_card[
        (subway_card['station_id_str'] == station_id) &
        (subway_card['in_out'].str.startswith('0'))
    ]

    if len(station_records) > 0:
        # 가장 빈도가 높은 좌표 사용 (mode)
        coords = station_records.groupby(['device_id']).size().reset_index(name='count')
        if len(coords) > 0:
            # device_id를 bus_routes에서 찾아 GPS 좌표 매핑
            # device_id는 정류소/역의 단말기 ID이므로 직접 사용

            # 대안: transport_name으로 노선 찾고 해당 노선의 station_name 매칭
            matching_routes = bus_routes[
                bus_routes['정류소명_clean'] == hub['station_name_clean']
            ]

            if len(matching_routes) > 0:
                hub_coords.at[idx, 'GPS_X'] = matching_routes.iloc[0]['GPS_X']
                hub_coords.at[idx, 'GPX_Y'] = matching_routes.iloc[0]['GPX_Y']

# 대안 2: 지하철역명에서 "지하철" 제거하고 버스정류소명과 매칭
for idx, hub in hub_coords[hub_coords['GPS_X'].isna()].iterrows():
    station_clean = hub['station_name'].replace('지하철', '').strip()

    # bus_routes에서 역명 매칭 (부분 매칭)
    matching = bus_routes[bus_routes['정류소명'].str.contains(station_clean, na=False, regex=False)]

    if len(matching) > 0:
        # 가장 많이 등장하는 좌표 사용
        coords_mode = matching.groupby(['GPS_X', 'GPX_Y']).size().reset_index(name='count')
        coords_mode = coords_mode.sort_values('count', ascending=False)

        hub_coords.at[idx, 'GPS_X'] = coords_mode.iloc[0]['GPS_X']
        hub_coords.at[idx, 'GPX_Y'] = coords_mode.iloc[0]['GPX_Y']

matched = hub_coords['GPS_X'].notna().sum()
print(f'\\n좌표 매핑 결과: {matched}/{len(hub_coords)}')

if matched < 10:
    print('\\n경고: 10개 미만의 환승거점 좌표만 매핑되었습니다.')
    print('매핑 실패한 거점:')
    print(hub_coords[hub_coords['GPS_X'].isna()][['station_name', '심야승차량']])
"""

# Update cell
nb['cells'][target_cell_idx]['source'] = new_code.split('\n')
nb['cells'][target_cell_idx]['outputs'] = []
nb['cells'][target_cell_idx]['execution_count'] = None

# Write back
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Cell 7.5 수정 완료 (index={target_cell_idx})")
print("환승 거점 좌표 매핑 로직을 bus_routes 기반으로 변경했습니다.")
