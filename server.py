from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
import json
import os
from functools import wraps

# ================= 설정 =================
# ★ 중요: 여기에 진짜 원하는 비밀번호를 적으세요
ADMIN_PASSWORD = "!!teastar??" 

# 암호화 키 (아무렇게나 복잡하게 적으세요)
SECRET_KEY = "my_super_secret_key_dominations"
# ========================================

# 템플릿 폴더를 현재 폴더('.')로 설정
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = SECRET_KEY

# 로그인 확인용 데코레이터 (입장권 검사기)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 1. 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('glory')) # 성공하면 순위표로 이동
        else:
            error = '비밀번호가 틀렸습니다.'
    
    # 간단한 로그인 화면 HTML
    return f'''
        <body style="background:#000; color:#fff; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif;">
            <div style="text-align:center; border:1px solid #444; padding:40px; border-radius:10px;">
                <h2 style="color:#facc15;">🔒 관계자 외 출입금지</h2>
                <form method="post">
                    <input type="password" name="password" placeholder="비밀번호" style="padding:10px; border-radius:5px; border:none;">
                    <button type="submit" style="padding:10px 20px; background:#facc15; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">접속</button>
                </form>
                <p style="color:red; margin-top:10px;">{error if error else ""}</p>
                <a href="/index.html" style="color:#888; text-decoration:none; font-size:12px;">← 메인으로 돌아가기</a>
            </div>
        </body>
    '''

# 2. 순위표 페이지 (보안 적용됨)
@app.route('/glory.html')
@app.route('/glory')
@login_required # <--- 이 줄 때문에 로그인 안 하면 절대 못 들어옴
def glory():
    # glory.html 파일을 읽어서 보여줌
    try:
        with open('glory.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "glory.html 파일을 찾을 수 없습니다."

# 3. 데이터 제공 (보안 적용됨)
@app.route('/get_data')
@login_required # <--- 데이터만 몰래 빼가는 것도 차단
def get_data():
    try:
        # JSON 파일을 읽어서 제공
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify({})

# 4. 메인 페이지 및 기타 파일 (누구나 접속 가능)
@app.route('/')
@app.route('/<path:filename>')
def serve_static(filename='index.html'):
    # glory.html로 직접 접속하려고 하면 로그인 체크 쪽으로 보냄
    if filename == 'glory.html':
        return redirect(url_for('glory'))
    return app.send_static_file(filename)

if __name__ == '__main__':
    # 서버 실행 (포트 5000번)
    print("🛡️ 보안 서버 가동 시작: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)