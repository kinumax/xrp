import os
from xumm import XummSdk
from flask import Blueprint, request, jsonify, session
import qrcode
import io
import base64
from src.models.user import db, User, Room, Comment

# Initialize XUMM SDK
xumm_api_key = os.getenv('XUMM_API_KEY', 'f45d63f3-7a2e-47ad-8b8c-11ce3f914b13')
xumm_api_secret = os.getenv('XUMM_API_SECRET', 'a36b9884-0c9f-43f2-91b7-bf742657e1e5')

try:
    xumm = XummSdk(xumm_api_key, xumm_api_secret)
except Exception as e:
    print(f"XUMM SDK initialization error: {e}")
    xumm = None

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/signin', methods=['POST'])
def signin():
    """XUMM認証用のサインリクエストを生成"""
    if not xumm:
        return jsonify({'success': False, 'error': 'XUMM SDK not initialized'}), 500
        
    try:
        # サインリクエストのペイロードを作成
        payload = {
            "txjson": {
                "TransactionType": "SignIn"
            },
            "options": {
                "submit": False,
                "multisign": False,
                "expire": 5  # 5分で期限切れ
            },
            "custom_meta": {
                "identifier": "voice-chat-signin",
                "blob": {},
                "instruction": "音声チャットアプリにサインインしてください"
            }
        }
        
        # XUMMにペイロードを送信
        created_payload = xumm.payload.create(payload)
        
        if created_payload and 'uuid' in created_payload:
            return jsonify({
                'success': True,
                'uuid': created_payload['uuid'],
                'next': created_payload['next'],
                'refs': created_payload['refs'],
                'pushed': created_payload['pushed']
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create payload'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/auth/verify/<uuid>', methods=['GET'])
def verify_signin(uuid):
    """サインリクエストの結果を確認し、ユーザーを登録/ログイン"""
    if not xumm:
        return jsonify({'success': False, 'error': 'XUMM SDK not initialized'}), 500
        
    try:
        # ペイロードの結果を取得
        payload_result = xumm.payload.get(uuid)
        
        if not payload_result:
            return jsonify({'success': False, 'error': 'Payload not found'}), 404
            
        if payload_result['meta']['signed']:
            # 署名されている場合、ユーザー情報を取得
            account = payload_result['response']['account']
            
            # ユーザーが既に存在するかチェック
            user = User.query.filter_by(xrp_wallet_address=account).first()
            
            if not user:
                # 新規ユーザーを作成
                user = User(xrp_wallet_address=account)
                db.session.add(user)
                db.session.commit()
            
            # セッションにユーザーIDを保存
            session['user_id'] = user.id
            
            return jsonify({
                'success': True,
                'signed': True,
                'user': user.to_dict()
            })
        else:
            return jsonify({
                'success': True,
                'signed': False,
                'message': 'Not signed yet'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    """ログアウト"""
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@auth_bp.route('/auth/me', methods=['GET'])
def get_current_user():
    """現在のユーザー情報を取得"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@auth_bp.route('/qr/wallet/<user_id>', methods=['GET'])
def generate_wallet_qr(user_id):
    """ユーザーのウォレットアドレス用QRコードを生成"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # QRコードを生成
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(user.xrp_wallet_address)
        qr.make(fit=True)
        
        # QRコード画像を作成
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Base64エンコード
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_code': f'data:image/png;base64,{qr_base64}',
            'wallet_address': user.xrp_wallet_address
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# テスト用のダミー認証エンドポイント（XUMM APIが利用できない場合）
@auth_bp.route('/auth/test-login', methods=['POST'])
def test_login():
    """テスト用のダミーログイン"""
    try:
        data = request.get_json()
        wallet_address = data.get('wallet_address', 'rTestWalletAddress123456789')
        
        # ユーザーが既に存在するかチェック
        user = User.query.filter_by(xrp_wallet_address=wallet_address).first()
        
        if not user:
            # 新規ユーザーを作成
            user = User(xrp_wallet_address=wallet_address)
            db.session.add(user)
            db.session.commit()
        
        # セッションにユーザーIDを保存
        session['user_id'] = user.id
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

