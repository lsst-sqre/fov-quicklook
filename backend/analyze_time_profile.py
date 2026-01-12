#!/usr/bin/env python3
"""
タイムプロファイルからガントチャートを生成するスクリプト

使用方法:
    python analyze_time_profile.py <time-profile.json> [-o output.html]
    python analyze_time_profile.py <time-profile.json> --text  # テキスト出力

タイムプロファイルJSON形式:
    {
        "visit_name": "raw:2026011000001",
        "start_time": "2026-01-12T10:00:00",
        "end_time": "2026-01-12T10:05:00",
        "ccd_profiles": [
            {
                "ccd_name": "R01_S00",
                "generator_id": "g-abc123",
                "assigned_at": "2026-01-12T10:00:01",
                "completed_at": "2026-01-12T10:00:15",
                "download_s": 2.5,
                "preprocess_s": 5.0,
                "generate_tiles_s": 3.0,
                "save_header_s": 0.1
            },
            ...
        ]
    }
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CcdProfile:
    ccd_name: str
    generator_id: str
    assigned_at: datetime | None
    completed_at: datetime | None
    download_s: float | None
    preprocess_s: float | None
    generate_tiles_s: float | None
    save_header_s: float | None

    @classmethod
    def from_dict(cls, d: dict) -> 'CcdProfile':
        return cls(
            ccd_name=d['ccd_name'],
            generator_id=d['generator_id'],
            assigned_at=datetime.fromisoformat(d['assigned_at']) if d.get('assigned_at') else None,
            completed_at=datetime.fromisoformat(d['completed_at']) if d.get('completed_at') else None,
            download_s=d.get('download_s'),
            preprocess_s=d.get('preprocess_s'),
            generate_tiles_s=d.get('generate_tiles_s'),
            save_header_s=d.get('save_header_s'),
        )

    @property
    def total_processing_time(self) -> float | None:
        times = [t for t in [self.download_s, self.preprocess_s, self.generate_tiles_s, self.save_header_s] if t is not None]
        return sum(times) if times else None


@dataclass
class VisitProfile:
    visit_name: str
    start_time: datetime
    end_time: datetime | None
    ccd_profiles: list[CcdProfile]

    @classmethod
    def from_dict(cls, d: dict) -> 'VisitProfile':
        return cls(
            visit_name=d['visit_name'],
            start_time=datetime.fromisoformat(d['start_time']),
            end_time=datetime.fromisoformat(d['end_time']) if d.get('end_time') else None,
            ccd_profiles=[CcdProfile.from_dict(p) for p in d.get('ccd_profiles', [])],
        )


def load_profile(path: Path) -> VisitProfile:
    with open(path) as f:
        data = json.load(f)
    return VisitProfile.from_dict(data)


def generate_text_report(profile: VisitProfile) -> str:
    """テキスト形式のレポートを生成"""
    lines = [
        f"Visit: {profile.visit_name}",
        f"Start: {profile.start_time.isoformat()}",
        f"End:   {profile.end_time.isoformat() if profile.end_time else 'N/A'}",
        f"Total CCDs: {len(profile.ccd_profiles)}",
        "",
        "=" * 120,
        f"{'CCD Name':<15} {'Generator':<20} {'Assigned':<25} {'Total (s)':<10} {'Download':<10} {'Preprocess':<10} {'GenTiles':<10} {'SaveHdr':<10}",
        "=" * 120,
    ]
    
    # generatorでソート、その中でassigned_atでソート
    sorted_profiles = sorted(
        profile.ccd_profiles,
        key=lambda p: (p.generator_id, p.assigned_at or datetime.min)
    )
    
    for p in sorted_profiles:
        total = p.total_processing_time
        lines.append(
            f"{p.ccd_name:<15} "
            f"{p.generator_id[:20]:<20} "
            f"{p.assigned_at.isoformat() if p.assigned_at else 'N/A':<25} "
            f"{total or 0:>9.2f} "
            f"{p.download_s or 0:>9.2f} "
            f"{p.preprocess_s or 0:>9.2f} "
            f"{p.generate_tiles_s or 0:>9.2f} "
            f"{p.save_header_s or 0:>9.2f}"
        )
    
    lines.append("=" * 120)
    
    # サマリー統計
    total_times = [p.total_processing_time for p in profile.ccd_profiles if p.total_processing_time is not None]
    if total_times:
        lines.append("")
        lines.append("Summary:")
        lines.append(f"  Total CCDs:     {len(profile.ccd_profiles)}")
        lines.append(f"  Min time (s):   {min(total_times):.2f}")
        lines.append(f"  Max time (s):   {max(total_times):.2f}")
        lines.append(f"  Mean time (s):  {sum(total_times) / len(total_times):.2f}")
        
        # Generator別統計
        generators = set(p.generator_id for p in profile.ccd_profiles)
        lines.append("")
        lines.append("Per-Generator Statistics:")
        for gen in sorted(generators):
            gen_profiles = [p for p in profile.ccd_profiles if p.generator_id == gen]
            gen_times = [p.total_processing_time for p in gen_profiles if p.total_processing_time is not None]
            if gen_times:
                lines.append(f"  {gen}: {len(gen_profiles)} CCDs, mean={sum(gen_times)/len(gen_times):.2f}s")
    
    return "\n".join(lines)


def generate_html_gantt(profile: VisitProfile) -> str:
    """HTML形式のガントチャートを生成"""
    if not profile.ccd_profiles:
        return "<html><body><p>No CCD profiles found</p></body></html>"
    
    # 基準時刻
    base_time = profile.start_time
    
    # Generator別にCCDをグループ化
    generators: dict[str, list[CcdProfile]] = {}
    for p in profile.ccd_profiles:
        if p.generator_id not in generators:
            generators[p.generator_id] = []
        generators[p.generator_id].append(p)
    
    # 各generator内でassigned_at順にソート
    for gen_id in generators:
        generators[gen_id].sort(key=lambda p: p.assigned_at or datetime.min)
    
    # 最大時間を計算
    max_seconds = 0
    for p in profile.ccd_profiles:
        if p.completed_at:
            seconds = (p.completed_at - base_time).total_seconds()
            max_seconds = max(max_seconds, seconds)
    
    if max_seconds == 0:
        max_seconds = 300  # デフォルト5分
    
    # スケール設定（ピクセル/秒）
    pixels_per_second = 5
    chart_width = int(max_seconds * pixels_per_second) + 100
    
    # 色の定義
    colors = {
        'download': '#4CAF50',      # 緑
        'preprocess': '#2196F3',    # 青
        'generate_tiles': '#FF9800', # オレンジ
        'save_header': '#9C27B0',   # 紫
        'unknown': '#9E9E9E',       # グレー
    }
    
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="UTF-8">',
        f'<title>Gantt Chart - {profile.visit_name}</title>',
        '<style>',
        'body { font-family: monospace; margin: 20px; }',
        '.gantt-container { overflow-x: auto; }',
        '.gantt-row { display: flex; align-items: center; margin: 2px 0; height: 20px; }',
        '.gantt-label { width: 200px; font-size: 11px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }',
        '.gantt-bars { position: relative; }',
        '.gantt-bar { position: absolute; height: 16px; top: 2px; opacity: 0.8; }',
        '.gantt-bar:hover { opacity: 1; }',
        '.time-axis { margin-left: 200px; margin-top: 10px; border-top: 1px solid #ccc; padding-top: 5px; }',
        '.time-tick { display: inline-block; width: 100px; font-size: 10px; }',
        '.legend { margin-top: 20px; }',
        '.legend-item { display: inline-block; margin-right: 20px; }',
        '.legend-color { display: inline-block; width: 20px; height: 12px; margin-right: 5px; vertical-align: middle; }',
        '.generator-group { margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }',
        '.generator-header { font-weight: bold; margin-bottom: 5px; color: #333; }',
        'h1 { font-size: 16px; }',
        'h2 { font-size: 14px; margin-top: 20px; }',
        '.summary { background: #f5f5f5; padding: 10px; margin-bottom: 20px; }',
        '</style>',
        '</head>',
        '<body>',
        f'<h1>Gantt Chart: {profile.visit_name}</h1>',
        '<div class="summary">',
        f'<p>Start: {profile.start_time.isoformat()}</p>',
        f'<p>End: {profile.end_time.isoformat() if profile.end_time else "N/A"}</p>',
        f'<p>Total CCDs: {len(profile.ccd_profiles)}</p>',
        f'<p>Generators: {len(generators)}</p>',
        '</div>',
        '<div class="legend">',
        f'<span class="legend-item"><span class="legend-color" style="background:{colors["download"]}"></span>Download</span>',
        f'<span class="legend-item"><span class="legend-color" style="background:{colors["preprocess"]}"></span>Preprocess</span>',
        f'<span class="legend-item"><span class="legend-color" style="background:{colors["generate_tiles"]}"></span>Generate Tiles</span>',
        f'<span class="legend-item"><span class="legend-color" style="background:{colors["save_header"]}"></span>Save Header</span>',
        '</div>',
        '<div class="gantt-container">',
    ]
    
    # Generator別にチャートを描画
    for gen_id in sorted(generators.keys()):
        gen_profiles = generators[gen_id]
        html_parts.append(f'<div class="generator-group">')
        html_parts.append(f'<div class="generator-header">{gen_id} ({len(gen_profiles)} CCDs)</div>')
        
        for p in gen_profiles:
            if not p.assigned_at:
                continue
            
            start_offset = (p.assigned_at - base_time).total_seconds()
            
            html_parts.append('<div class="gantt-row">')
            html_parts.append(f'<div class="gantt-label" title="{p.ccd_name}">{p.ccd_name}</div>')
            html_parts.append(f'<div class="gantt-bars" style="width:{chart_width}px;">')
            
            # 各フェーズのバーを描画
            current_offset = start_offset
            phases = [
                ('download', p.download_s, colors['download']),
                ('preprocess', p.preprocess_s, colors['preprocess']),
                ('generate_tiles', p.generate_tiles_s, colors['generate_tiles']),
                ('save_header', p.save_header_s, colors['save_header']),
            ]
            
            for phase_name, duration, color in phases:
                if duration and duration > 0:
                    left = current_offset * pixels_per_second
                    width = duration * pixels_per_second
                    title = f"{phase_name}: {duration:.2f}s"
                    html_parts.append(
                        f'<div class="gantt-bar" style="left:{left}px;width:{max(width, 1)}px;background:{color};" title="{title}"></div>'
                    )
                    current_offset += duration
            
            html_parts.append('</div>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
    
    # 時間軸
    html_parts.append('<div class="time-axis">')
    for i in range(0, int(max_seconds) + 1, 30):
        html_parts.append(f'<span class="time-tick">{i}s</span>')
    html_parts.append('</div>')
    
    html_parts.append('</div>')
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    return '\n'.join(html_parts)


def main():
    parser = argparse.ArgumentParser(description='Generate Gantt chart from time profile JSON')
    parser.add_argument('profile_json', type=Path, help='Path to time profile JSON file')
    parser.add_argument('-o', '--output', type=Path, help='Output file path (default: stdout)')
    parser.add_argument('--text', action='store_true', help='Output text report instead of HTML')
    args = parser.parse_args()
    
    if not args.profile_json.exists():
        print(f"Error: File not found: {args.profile_json}", file=sys.stderr)
        sys.exit(1)
    
    profile = load_profile(args.profile_json)
    
    if args.text:
        output = generate_text_report(profile)
    else:
        output = generate_html_gantt(profile)
    
    if args.output:
        args.output.write_text(output)
        print(f"Output written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
