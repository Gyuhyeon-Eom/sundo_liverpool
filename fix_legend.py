import json

# 노트북 읽기
with open('busan_transit_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# 7.7 시각화 셀 찾기
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code' and '# 7.7 신규 노선 시각화' in ''.join(cell['source']):
        # 새로운 시각화 코드
        new_code = [
            "# 7.7 신규 노선 시각화\n",
            "if len(new_candidates) > 0 and 'cluster' in new_candidates.columns:\n",
            "    fig, ax = plt.subplots(1, 1, figsize=(14, 16))\n",
            "    \n",
            "    # 배경: 전체 집계구\n",
            "    census.plot(ax=ax, color='lightgray', edgecolor='white', linewidth=0.3, alpha=0.5)\n",
            "    \n",
            "    # 기존 심야버스 서비스 권역\n",
            "    if night_service_area is not None and not night_service_area.is_empty:\n",
            "        gpd.GeoSeries([night_service_area], crs='EPSG:5179').plot(\n",
            "            ax=ax, color='yellow', alpha=0.2, edgecolor='orange', linewidth=1.5, label='기존 심야버스 권역 (500m)'\n",
            "        )\n",
            "    \n",
            "    # 신규 후보지역 (클러스터별 색상)\n",
            "    cluster_handles = []\n",
            "    if new_candidates['cluster'].max() >= 0:\n",
            "        clusters = new_candidates[new_candidates['cluster'] >= 0]\n",
            "        \n",
            "        # 클러스터별로 그리고 범례 핸들 생성\n",
            "        from matplotlib.patches import Patch\n",
            "        import matplotlib.cm as cm\n",
            "        \n",
            "        n_clusters = clusters['cluster'].nunique()\n",
            "        colors = cm.tab10(range(n_clusters))\n",
            "        \n",
            "        for idx, cluster_id in enumerate(sorted(clusters['cluster'].unique())):\n",
            "            cluster_data = clusters[clusters['cluster'] == cluster_id]\n",
            "            color = colors[idx % 10]\n",
            "            \n",
            "            cluster_data.plot(\n",
            "                ax=ax, color=color, edgecolor='black', linewidth=0.8, alpha=0.7\n",
            "            )\n",
            "            \n",
            "            # 범례 핸들 추가\n",
            "            cluster_handles.append(\n",
            "                Patch(facecolor=color, edgecolor='black', label=f'클러스터 {cluster_id} ({len(cluster_data)}개)')\n",
            "            )\n",
            "    \n",
            "    # 노이즈 포인트 (클러스터 미포함)\n",
            "    noise = new_candidates[new_candidates['cluster'] == -1]\n",
            "    if len(noise) > 0:\n",
            "        noise.plot(ax=ax, color='red', edgecolor='darkred', linewidth=0.5, alpha=0.5)\n",
            "        from matplotlib.patches import Patch\n",
            "        cluster_handles.append(\n",
            "            Patch(facecolor='red', edgecolor='darkred', label=f'비클러스터 지역 ({len(noise)}개)')\n",
            "        )\n",
            "    \n",
            "    # 환승 거점\n",
            "    if len(hub_coords[hub_coords['GPS_X'].notna()]) > 0:\n",
            "        hub_gdf = gpd.GeoDataFrame(\n",
            "            hub_coords[hub_coords['GPS_X'].notna()],\n",
            "            geometry=[Point(row['GPS_X'], row['GPX_Y']) for _, row in hub_coords[hub_coords['GPS_X'].notna()].iterrows()],\n",
            "            crs='EPSG:4326'\n",
            "        ).to_crs('EPSG:5179')\n",
            "        \n",
            "        hub_gdf.plot(ax=ax, color='blue', marker='*', markersize=200, \n",
            "                     edgecolor='white', linewidth=1.5, zorder=5)\n",
            "        \n",
            "        # 환승 거점 범례\n",
            "        from matplotlib.lines import Line2D\n",
            "        hub_handle = Line2D([0], [0], marker='*', color='w', markerfacecolor='blue', \n",
            "                           markeredgecolor='white', markersize=15, label=f'환승 거점 ({len(hub_gdf)}개)')\n",
            "        cluster_handles.append(hub_handle)\n",
            "    \n",
            "    ax.set_title('신규 심야노선 후보지역 및 환승거점', fontsize=16, fontweight='bold', pad=20)\n",
            "    \n",
            "    # 범례 설정\n",
            "    if cluster_handles:\n",
            "        ax.legend(handles=cluster_handles, loc='upper right', fontsize=9, \n",
            "                 framealpha=0.9, title='범례', title_fontsize=10)\n",
            "    \n",
            "    ax.set_axis_off()\n",
            "    \n",
            "    plt.tight_layout()\n",
            "    plt.savefig(f'{BASE}/fig_06_new_night_routes.png', dpi=150, bbox_inches='tight')\n",
            "    plt.show()\n",
            "    print('저장: fig_06_new_night_routes.png')\n",
            "else:\n",
            "    print('시각화할 데이터가 없습니다.')"
        ]

        nb['cells'][i]['source'] = new_code
        print(f'셀 {i} 수정 완료')
        break

# 노트북 저장
with open('busan_transit_analysis.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('범례 수정 완료')
