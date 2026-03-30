import json

# Read notebook
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find cells to update
cells_to_update = {}

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])

        # Section 6 Cell #44: 심야 승차량 분석
        if "print(f'=== 심야 승차량 상위 30 정류소/역 ===')" in source and 'night_station.head(30)' in source:
            cells_to_update['6_station'] = i

        # Section 6 Cell #46: 집계구별 심야수요 매핑
        elif 'night_spatial_gdf = gpd.GeoDataFrame' in source and 'night_per_census' in source:
            cells_to_update['6_demand'] = i

print(f"찾은 셀: {cells_to_update}")

if len(cells_to_update) < 2:
    print("일부 셀을 찾지 못했습니다.")
    exit(1)

# New code for Cell #44: 버스 정류소만 분석
new_cell_44 = """# 심야 승차량 상위 정류소 (정류소/역별)
night_station = night_boarding.groupby(['station_id', 'station_name'])['passenger_type'].count().reset_index()
night_station.columns = ['station_id', 'station_name', '심야승차량']
night_station = night_station.sort_values('심야승차량', ascending=False)

print(f'=== 심야 승차량 상위 30 정류소/역 (전체) ===')
print(night_station.head(30)[['station_id', 'station_name', '심야승차량']].to_string(index=False))

print(f'\\n심야 승차 기록 있는 정류소/역: {len(night_station)}개')

# 버스 정류소만 필터링 (지하철역 제외)
bus_night_station = night_station[~night_station['station_name'].str.contains('지하철', na=False)].copy()

print(f'\\n=== 심야 승차량 상위 30 버스 정류소 (지하철 제외) ===')
print(bus_night_station.head(30)[['station_id', 'station_name', '심야승차량']].to_string(index=False))

print(f'\\n심야 이용 버스 정류소: {len(bus_night_station)}개')

# 지하철역 참고 (환승 연계 분석용)
subway_night_station = night_station[night_station['station_name'].str.contains('지하철', na=False)].copy()
print(f'\\n[참고] 심야 이용 지하철역: {len(subway_night_station)}개')
print(subway_night_station.head(10)[['station_name', '심야승차량']].to_string(index=False))
"""

# New code for Cell #46: 버스 정류소 좌표만 사용
new_cell_46 = """# 심야수요를 집계구에 매핑 (버스 정류소 기반)

# 버스 정류소만 사용 (지하철역 제외)
bus_night_station['station_id_str'] = bus_night_station['station_id'].astype(str).str.zfill(7)
bus_night_station['station_name_clean'] = bus_night_station['station_name'].str.strip()

# bus_routes에서 정류소명으로 매칭하여 좌표 얻기
night_spatial = bus_night_station.merge(
    bus_routes[['정류소명_clean', 'GPS_X', 'GPX_Y']].drop_duplicates('정류소명_clean'),
    left_on='station_name_clean',
    right_on='정류소명_clean',
    how='left'
)

# 좌표가 있는 정류소만
night_spatial['has_coords'] = night_spatial['GPS_X'].notna()
night_with_coords = night_spatial[night_spatial['has_coords']].copy()

matched = len(night_with_coords)
total = len(bus_night_station)
print(f'좌표 매핑 결과: {matched}/{total} ({matched/total*100:.1f}%)')
print(f'변환된 버스 정류소 수: {matched}')

# GeoDataFrame 생성
if len(night_with_coords) > 0:
    night_spatial_gdf = gpd.GeoDataFrame(
        night_with_coords,
        geometry=[Point(row['GPS_X'], row['GPX_Y']) for _, row in night_with_coords.iterrows()],
        crs='EPSG:4326'
    ).to_crs('EPSG:5179')

    # 집계구와 공간 조인
    night_in_census = gpd.sjoin(night_spatial_gdf, census, how='inner', predicate='within')

    # 집계구별 심야수요 합계
    night_per_census = night_in_census.groupby('TOT_REG_CD')['심야승차량'].sum().reset_index()
    night_per_census.columns = ['TOT_REG_CD', '심야수요']

    print(f'\\n심야 수요 있는 집계구: {len(night_per_census)}개')

    # census_with_stops에 심야수요 추가
    census_with_stops = census_with_stops.merge(night_per_census, on='TOT_REG_CD', how='left')
    census_with_stops['심야수요'] = census_with_stops['심야수요'].fillna(0).astype(int)

    # 면적당 심야수요 밀도
    census_with_stops['심야수요밀도'] = census_with_stops['심야수요'] / census_with_stops['면적_km2']
    census_with_stops['심야수요밀도'] = census_with_stops['심야수요밀도'].replace([np.inf, -np.inf], 0)

    print(f'\\n심야 수요 상위 10 집계구:')
    top_demand = census_with_stops.nlargest(10, '심야수요')[['TOT_REG_CD', '심야수요', '정류소수', '커버리지']]
    print(top_demand.to_string(index=False))
else:
    print('\\n경고: 좌표 매핑 실패로 심야수요 분석을 수행할 수 없습니다.')
"""

# Update cells
nb['cells'][cells_to_update['6_station']]['source'] = new_cell_44.split('\n')
nb['cells'][cells_to_update['6_station']]['outputs'] = []
nb['cells'][cells_to_update['6_station']]['execution_count'] = None

nb['cells'][cells_to_update['6_demand']]['source'] = new_cell_46.split('\n')
nb['cells'][cells_to_update['6_demand']]['outputs'] = []
nb['cells'][cells_to_update['6_demand']]['execution_count'] = None

# Write back
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\\nCell 업데이트 완료:")
print(f"- Cell #{cells_to_update['6_station']}: 심야 승차량 분석 (버스 정류소 중심)")
print(f"- Cell #{cells_to_update['6_demand']}: 집계구별 심야수요 (버스 정류소만)")
print("\\n변경 내용:")
print("- 버스 정류소와 지하철역 분리")
print("- 버스 정류소 기반 심야수요 집계")
print("- 지하철역은 참고용으로만 출력")
