def apply_policy(condition_state: str) -> dict:
    # UI 모드 정의: 카드 수, 알림 강도 등 (기존 형식 유지)
    
    # 1. 정상/안정 상태 (TENSE/DEFAULT 매칭)
    if condition_state == "normal" or condition_state == "tense":
        return {
            "ui_mode": "calm", 
            "label": "안정 (NORMAL)", # 한글 병기
            "message": "컨디션이 아주 좋아 보여요! 오늘 하루도 파이팅입니다. 👍",
            "max_cards": 3, "alert_strength": "mid", "tone": "reassuring"
        }
    
    # 2. 피로/졸음 상태 (TIRED/DROWSY 매칭)
    if condition_state == "drowsy" or condition_state == "tired":
        return {
            "ui_mode": "compact", 
            "label": "주의 (DROWSY)", # 한글 병기
            "message": "조금 피곤해 보이시네요. 잠시 휴식을 취하는 건 어떨까요? ☕",
            "max_cards": 2, "alert_strength": "low", "tone": "short"
        }
    
    # 3. 응답 없음/식별 중
    if condition_state == "noresponse":
        return {
            "ui_mode": "prompt", 
            "label": "확인 중",
            "message": "사용자의 반응을 기다리고 있습니다.",
            "max_cards": 2, "alert_strength": "mid", "tone": "call"
        }
    
    # 4. 얼굴 없음
    if condition_state == "noface":
        return {
            "ui_mode": "idle", 
            "label": "대기 중",
            "message": "거울 앞에 서면 분석을 시작합니다.",
            "max_cards": 1, "alert_strength": "low", "tone": "idle"
        }
    
    # 기본값
    return {
        "ui_mode": "default", 
        "label": "분석 중",
        "message": "상태를 정밀 분석하고 있습니다.",
        "max_cards": 4, "alert_strength": "mid", "tone": "normal"
    }
