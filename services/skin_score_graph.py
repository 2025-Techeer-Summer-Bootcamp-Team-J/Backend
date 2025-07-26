import json
import matplotlib.pyplot as plt
import numpy as np

def plot_score_radar(score_info: dict, title: str = '피부 점수 레이더 차트'):
    """
    score_info 딕셔너리를 받아 주요 항목을 레이더 차트로 시각화합니다.
    title: 그래프 제목
    """
    labels = [
        "dark_circle_score", "skin_type_score", "wrinkle_score", "oily_intensity_score",
        "pores_score", "blackhead_score", "acne_score", "sensitivity_score",
        "melanin_score", "water_score", "rough_score", "total_score"
    ]
    values = [score_info[label] for label in labels]
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values, 'o-', linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    # set_thetagrids에 마지막 중복 각도는 빼고 전달
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    plt.title(title)
    plt.savefig("output/skin_score_radar.png")
    return
# 예시 사용법 (response_json.txt에서 score_info 읽어서 시각화)
if __name__ == "__main__":
    with open("output/response_json.txt", "r", encoding="utf-8") as f:
        data = json.load(f)
    score_info = data["score_info"]
    plot_score_radar(score_info) 