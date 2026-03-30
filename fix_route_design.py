import json

# Read notebook
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find Cell 7.5 and 7.6
cell_75_idx = None
cell_76_idx = None

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if '# 7.5 주요 환승 거점 선정 (시작점/종점 후보)' in source:
            if cell_75_idx is None:  # 첫 번째 발견은 건너뛰고 두 번째 것 사용
                cell_75_idx = -1
            elif cell_75_idx == -1:
                cell_75_idx = i
        elif '# 7.6 신규 노선 경로 설계 (클러스터별 + 최근접 환승거점 연결)' in source:
            if cell_76_idx is None:  # 첫 번째 발견은 건너뛰고 두 번째 것 사용
                cell_76_idx = -1
            elif cell_76_idx == -1:
                cell_76_idx = i

if cell_75_idx is None or cell_76_idx is None:
    print(f"Cell을 찾을 수 없습니다. 75={cell_75_idx}, 76={cell_76_idx}")
    exit(1)

# New Cell 7.5: 클러스터별 대표 정류소 선정
new_cell_75 = """# 7.5 클러스터별 대표 버스 정류소 선정

# 각 클러스터의 중심에 가장 가까운 버스 정류소 찾기
cluster_stops = []

for cluster_id in sorted(new_candidates['cluster'].unique()):
    if cluster_id == -1:  # 노이즈 제외
        continue

    cluster_data = new_candidates[new_candidates['cluster'] == cluster_id]
    cluster_center = cluster_data['centroid'].unary_union.centroid

    # 클러스터 내 집계구들과 인접한 버스 정류소 찾기
    # buffer를 이용해 클러스터 영역 생성
    cluster_area = cluster_data.unary_union.buffer(500)  # 500m 버퍼

    # 해당 영역 내의 버스 정류소 찾기
    stops_in_cluster = bus_stops_shp[bus_stops_shp.intersects(cluster_area)].copy()

    if len(stops_in_cluster) > 0:
        # 클러스터 중심에서 가장 가까운 정류소 3개 선정
        stops_in_cluster['dist_to_center'] = stops_in_cluster.geometry.distance(cluster_center)
        top_stops = stops_in_cluster.nsmallest(3, 'dist_to_center')

        cluster_stops.append({
            '클러스터ID': cluster_id,
            '집계구수': len(cluster_data),
            '총상업시설': cluster_data['상업시설'].sum(),
            '총심야수요': cluster_data['심야수요'].sum(),
            '대표정류소수': len(top_stops),
            '중심좌표_x': cluster_center.x,
            '중심좌표_y': cluster_center.y,
            '대표정류소': list(top_stops['bstopnm'].values),
            '정류소좌표': list(zip(top_stops.geometry.x, top_stops.geometry.y))
        })

cluster_summary = pd.DataFrame(cluster_stops)
cluster_summary = cluster_summary.sort_values('총상업시설', ascending=False)

print(f'=== 클러스터별 대표 정류소 ===')
print(f'총 {len(cluster_summary)}개 클러스터\\n')
print(cluster_summary[['클러스터ID', '집계구수', '총상업시설', '총심야수요', '대표정류소수']])

# 심야 이용이 많은 버스 정류소 (환승 거점용)
bus_night_stops = night_station[~night_station['station_name'].str.contains('지하철', na=False)].copy()
bus_night_stops = bus_night_stops.nlargest(20, '심야승차량')

print(f'\\n=== 심야 이용 상위 버스 정류소 (Top 20) ===')
print(bus_night_stops[['station_name', '심야승차량']].head(10))
"""

# New Cell 7.6: 클러스터 기반 노선 설계
new_cell_76 = """# 7.6 신규 노선 설계 (클러스터 연결형)

# 방식: 각 클러스터의 대표 정류소들을 연결하여 순환 노선 설계
# 큰 클러스터들을 우선적으로 연결

if len(cluster_summary) > 0:

    new_routes = []

    # 방법 1: 각 클러스터를 독립 노선으로 설계 (클러스터당 1개 노선)
    for idx, cluster_info in cluster_summary.iterrows():
        cluster_id = cluster_info['클러스터ID']

        # 클러스터가 일정 규모 이상인 경우만 노선 제안
        if cluster_info['집계구수'] >= 3:

            route_info = {
                '노선ID': f'신규심야{cluster_id+1}',
                '클러스터ID': cluster_id,
                '집계구수': cluster_info['집계구수'],
                '총상업시설': cluster_info['총상업시설'],
                '총심야수요': cluster_info['총심야수요'],
                '경유정류소수': cluster_info['대표정류소수'],
                '대표정류소': ', '.join(cluster_info['대표정류소'][:3]),
                '노선유형': '클러스터순환형'
            }

            new_routes.append(route_info)

    # 방법 2: 인접한 클러스터들을 묶어서 노선 설계
    # (클러스터 간 거리가 5km 이내인 경우 하나의 노선으로 통합)
    if len(cluster_summary) >= 2:
        from scipy.spatial.distance import cdist

        # 클러스터 중심 좌표
        centers = cluster_summary[['중심좌표_x', '중심좌표_y']].values

        # 클러스터 간 거리 행렬
        dist_matrix = cdist(centers, centers, metric='euclidean')

        # 거리 5km 이내 클러스터 그룹핑
        threshold = 5000  # 5km
        cluster_groups = []
        visited = set()

        for i in range(len(cluster_summary)):
            if i in visited:
                continue

            # i번째 클러스터와 가까운 클러스터들 찾기
            group = [i]
            visited.add(i)

            for j in range(len(cluster_summary)):
                if j != i and j not in visited and dist_matrix[i][j] < threshold:
                    group.append(j)
                    visited.add(j)

            if len(group) >= 1:
                cluster_groups.append(group)

        # 그룹별 통합 노선 제안
        for g_idx, group in enumerate(cluster_groups):
            group_clusters = cluster_summary.iloc[group]

            total_areas = group_clusters['집계구수'].sum()
            total_commercial = group_clusters['총상업시설'].sum()
            total_demand = group_clusters['총심야수요'].sum()

            if total_areas >= 5:  # 충분한 규모
                route_info = {
                    '노선ID': f'신규심야통합{g_idx+1}',
                    '클러스터ID': f"C{'+'.join(map(str, group_clusters['클러스터ID'].values))}",
                    '집계구수': total_areas,
                    '총상업시설': total_commercial,
                    '총심야수요': total_demand,
                    '경유정류소수': group_clusters['대표정류소수'].sum(),
                    '대표정류소': '다수',
                    '노선유형': '클러스터연결형'
                }

                new_routes.append(route_info)

    # 결과 출력
    if new_routes:
        routes_df = pd.DataFrame(new_routes)
        routes_df = routes_df.sort_values('총상업시설', ascending=False)

        print(f'=== 신규 심야노선 설계 결과 ===')
        print(f'총 {len(routes_df)}개 노선 제안\\n')
        print(routes_df[['노선ID', '집계구수', '총상업시설', '총심야수요', '노선유형']])

        # CSV 저장
        routes_df.to_csv(f'{BASE}/result_신규심야노선_제안.csv', index=False, encoding='utf-8-sig')
        print(f'\\n저장: result_신규심야노선_제안.csv')
    else:
        print('설계 가능한 노선이 없습니다.')
else:
    print('클러스터 데이터가 없습니다.')
"""

# Update cells
nb['cells'][cell_75_idx]['source'] = new_cell_75.split('\n')
nb['cells'][cell_75_idx]['outputs'] = []
nb['cells'][cell_75_idx]['execution_count'] = None

nb['cells'][cell_76_idx]['source'] = new_cell_76.split('\n')
nb['cells'][cell_76_idx]['outputs'] = []
nb['cells'][cell_76_idx]['execution_count'] = None

# Write back
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Cell 7.5 (index={cell_75_idx}) 수정 완료")
print(f"Cell 7.6 (index={cell_76_idx}) 수정 완료")
print("\\n변경 내용:")
print("- 7.5: 클러스터별 대표 버스 정류소 선정 (환승거점 대신)")
print("- 7.6: 클러스터 연결형 버스 노선 설계 (독립노선 + 통합노선)")
