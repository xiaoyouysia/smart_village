import re
from typing import Dict, List, Any

INDUSTRY_PROFILES = {
    "现代农业": {
        "keywords": [
            "农业", "耕地", "粮食", "种植", "农产品", "产值", "农业产值",
            "农业人口", "水稻", "蔬菜", "果树", "农田", "农机"
        ],
        "description": "发挥农村土地与农业资源优势，推动现代农业、设施农业和订单农业。"
    },
    "乡村旅游": {
        "keywords": [
            "旅游", "景区", "接待", "乡村旅游", "民宿", "文化", "特色小镇",
            "景点", "游客", "旅游收入", "旅游人数"
        ],
        "description": "依托自然与文化资源发展乡村旅游、民宿、休闲度假和特色活动。"
    },
    "生态养殖": {
        "keywords": [
            "养殖", "林业", "生态", "水产", "渔业", "畜牧", "绿色", "生态养殖",
            "种植养殖", "草场", "林木"
        ],
        "description": "发展生态养殖、林下经济与绿色农业，实现资源循环与环境友好。"
    },
    "农村电商": {
        "keywords": [
            "电商", "互联网", "网店", "网络", "快递", "直播", "电商交易", "物流", "信息化"
        ],
        "description": "推动农产品上行、电商直播、物流配送与农村信息化建设。"
    },
    "特色加工": {
        "keywords": [
            "加工业", "加工", "特色", "手工", "深加工", "品牌", "产品加", "农产品加工"
        ],
        "description": "打造特色加工产业链，提升农产品附加值，发展乡村产业集群。"
    }
}

DEFAULT_TARGET_MAX = 1000.0


def _lower_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip().lower()


def _guess_target_max(indicator_name: str) -> float:
    name = _lower_text(indicator_name)
    if any(keyword in name for keyword in ["比例", "率", "占比", "份额"]):
        return 100.0
    if any(keyword in name for keyword in ["面积", "亩", "公顷", "平方"]):
        return 1000.0
    if any(keyword in name for keyword in ["人", "人数", "人口", "户"]):
        return 10000.0
    if any(keyword in name for keyword in ["产值", "收入", "规模", "交易", "销售"]):
        return 10000.0
    return DEFAULT_TARGET_MAX


def _normalize_value(value: Any, target_max: float) -> float:
    try:
        real_value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if real_value <= 0:
        return 0.0
    if target_max <= 0:
        return 0.0
    return min(real_value / target_max, 1.0)


def _match_indicator_score(indicator_name: str, category_l1: str, category_l2: str, keywords: List[str]) -> int:
    lower_name = _lower_text(indicator_name)
    lower_cat1 = _lower_text(category_l1)
    lower_cat2 = _lower_text(category_l2)
    score = 0
    for keyword in keywords:
        if keyword in lower_name or keyword in lower_cat1 or keyword in lower_cat2:
            score += 1
    return score


def _collect_profile_scores(indicator_values: Dict[int, float], definitions: Dict[int, Any]) -> Dict[str, Any]:
    scores: Dict[str, float] = {name: 0.0 for name in INDUSTRY_PROFILES}
    weight_sum: Dict[str, float] = {name: 0.0 for name in INDUSTRY_PROFILES}
    indicators_detail: Dict[str, List[str]] = {name: [] for name in INDUSTRY_PROFILES}

    for indicator_id, value in indicator_values.items():
        definition = definitions.get(indicator_id)
        if not definition:
            continue

        indicator_name = getattr(definition, 'indicator_name', '')
        category_l1 = getattr(definition, 'category_l1', '')
        category_l2 = getattr(definition, 'category_l2', '')
        target_max = _guess_target_max(indicator_name)
        normalized_value = _normalize_value(value, target_max)

        for industry_name, profile in INDUSTRY_PROFILES.items():
            hit = _match_indicator_score(indicator_name, category_l1, category_l2, profile['keywords'])
            if hit <= 0:
                continue

            score = normalized_value * float(hit)
            scores[industry_name] += score
            weight_sum[industry_name] += hit
            indicators_detail[industry_name].append(f"{indicator_name}: {value}")

    return {
        'scores': scores,
        'weight_sum': weight_sum,
        'indicators_detail': indicators_detail
    }


def recommend_industries(indicator_values: Dict[int, float], definitions: Dict[int, Any], top_n: int = 3) -> List[Dict[str, Any]]:
    """根据村庄指标推荐适合的产业。"""
    result = _collect_profile_scores(indicator_values, definitions)
    scores = result['scores']
    weight_sum = result['weight_sum']
    details = result['indicators_detail']

    recommendations = []
    for industry_name, raw_score in scores.items():
        if weight_sum[industry_name] > 0:
            average_score = raw_score / weight_sum[industry_name]
            coverage_bonus = min(weight_sum[industry_name] / 5.0, 1.0)
            final_score = round(float(average_score * 0.8 + coverage_bonus * 0.2), 4)
        else:
            final_score = 0.0

        recommendations.append({
            'industry': industry_name,
            'description': INDUSTRY_PROFILES[industry_name]['description'],
            'score': final_score,
            'matched_indicators': details[industry_name][:5]
        })

    if all(item['score'] == 0.0 for item in recommendations):
        for item in recommendations:
            item['score'] = 0.1

    recommendations.sort(key=lambda item: item['score'], reverse=True)
    return recommendations[:max(1, min(top_n, len(recommendations)))]
