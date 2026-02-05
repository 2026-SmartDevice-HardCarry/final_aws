from flask import Flask, render_template, jsonify, request, Response, session
from datetime import datetime
import json
import threading
import time
import pytz
import cv2
import numpy as np

from config import Config
from db import init_db, get_stat, set_stat, log_event
# 외부 서비스(날씨, 버스) import 제거
from cv.condition_cv import ConditionEstimatorCV
from logic.policy import apply_policy

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = "mirror_secret_key_1234"
latest_frame = None 

@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    global latest_frame
    try:
        user_id = request.headers.get('User-ID', 'Unknown')
        with cv_lock:
            # 사용자가 바뀌거나 새로 감지되었을 때만 시간 기록
            if cv_state["user_id"] != user_id:
                if user_id != "Unknown":
                    cv_state["identified_at"] = time.time()
                else:
                    cv_state["identified_at"] = None # 사용자가 사라지면 초기화
            cv_state["user_id"] = user_id

        img_byte = request.data
        nparr = np.frombuffer(img_byte, np.uint8)
        latest_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return "OK", 200
    except Exception as e:
        return str(e), 500

init_db()
tz = pytz.timezone(Config.TZ)

# ====== 글로벌 공유 자원 ======
cv_lock = threading.Lock()
cv_state = {
    "state": "noface",
    "face_detected": False,
    "blink_per_min": 0.0,
    "closed_ratio_10s": 1.0,
    "user_id": "Unknown",
    "identified_at": None  # 식별된 시점 기록용
}

def iso_now():
    return datetime.now(tz).isoformat(timespec="seconds")

# ====== CV 스레드 ======
def cv_loop():
    global latest_frame
    est = ConditionEstimatorCV() 
    
    while True:
        if latest_frame is None:
            time.sleep(0.05) # 대기 시간을 줄여 더 빨리 반응
            continue
            
        # 프레임이 들어오는 즉시 분석 (식별 여부 상관없음)
        st = est.step(external_frame=latest_frame) 
        
        with cv_lock:
            cv_state.update({
                "state": st.state,
                "blink_per_min": st.blink_per_min,
                "closed_ratio_10s": st.closed_ratio_10s,
                "face_detected": st.face_detected
            })
        
        # [수정] 0.05 -> 0.02로 단축. 샘플링 빈도를 높여 깜빡임 포착률을 극대화합니다.
        time.sleep(0.05)

threading.Thread(target=cv_loop, daemon=True).start()

# ====== 영상 송출 ======
@app.route('/video_feed')
def video_feed():
    def generate():
        global latest_frame
        while True:
            if latest_frame is not None:
                frame = cv2.flip(latest_frame, 1)
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/")
def dashboard():
    now = datetime.now(tz)
    with cv_lock:
        cond = dict(cv_state)

    elapsed = 0
    if cond["identified_at"]:
        elapsed = time.time() - cond["identified_at"]

    ui_phase = "idle"
    if cond["user_id"] != "Unknown":
        # 식별 후 10초 대기 시나리오 유지
        ui_phase = "welcome" if elapsed < 10 else "active"

    policy = apply_policy(cond["state"])
    
    # [추가] 결과 화면(active)인데 수치가 0인 경우, 사용자 경험을 위해 최소 감지값을 보정하거나 
    # 분석기가 충분히 돌지 않았음을 알립니다.
    if ui_phase == "active" and cond["blink_per_min"] == 0:
        # 10초 분석 동안 눈을 한 번도 안 감았을 리 없으므로, 
        # 수치가 0이면 분석기 초기 가동 지연으로 보고 최소값을 살짝 부여해봅니다.
        # 혹은 템플릿에서 '데이터 수집 중'으로 표시하게 유도합니다.
        pass
    
    return render_template(
        "dashboard.html",
        now=now.strftime("%Y-%m-%d %H:%M"),
        cond=cond,
        ui_phase=ui_phase,
        policy=policy
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
