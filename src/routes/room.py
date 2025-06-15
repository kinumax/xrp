from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Room, Comment

room_bp = Blueprint('room', __name__)

def require_auth():
    """認証が必要なエンドポイント用のデコレータ"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

@room_bp.route('/rooms', methods=['GET'])
def get_rooms():
    """ルーム一覧を取得"""
    try:
        rooms = Room.query.order_by(Room.created_at.desc()).all()
        return jsonify({
            'success': True,
            'rooms': [room.to_dict() for room in rooms]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@room_bp.route('/rooms', methods=['POST'])
def create_room():
    """新しいルームを作成"""
    user = require_auth()
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        room_name = data.get('room_name')
        
        if not room_name:
            return jsonify({'success': False, 'error': 'Room name is required'}), 400
        
        # 新しいルームを作成
        room = Room(
            host_user_id=user.id,
            room_name=room_name
        )
        db.session.add(room)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'room': room.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@room_bp.route('/rooms/<room_id>', methods=['GET'])
def get_room(room_id):
    """特定のルーム情報を取得"""
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'error': 'Room not found'}), 404
        
        return jsonify({
            'success': True,
            'room': room.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@room_bp.route('/rooms/<room_id>/comments', methods=['GET'])
def get_room_comments(room_id):
    """ルームのコメント一覧を取得"""
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'error': 'Room not found'}), 404
        
        comments = Comment.query.filter_by(room_id=room_id).order_by(Comment.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@room_bp.route('/rooms/<room_id>/comments', methods=['POST'])
def add_comment(room_id):
    """ルームにコメントを追加"""
    user = require_auth()
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'error': 'Room not found'}), 404
        
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # 新しいコメントを作成
        comment = Comment(
            room_id=room_id,
            user_id=user.id,
            message=message
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

