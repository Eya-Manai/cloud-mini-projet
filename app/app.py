from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import redis
import os
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://admin:admin@db:5432/tasks'
)

db = SQLAlchemy(app)

r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, decode_responses=True)

class Task(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    done  = db.Column(db.Boolean, default=False)

import time

def init_db():
    retries = 20       
    while retries > 0:
        try:
            with app.app_context():
                db.create_all()
            print("Base de données connectée !")
            return
        except Exception as e:
            print(f" Attente DB... ({e})")
            retries -= 1
            time.sleep(5) 
    print("❌ Impossible de connecter la base de données")

init_db()

@app.route('/tasks', methods=['GET'])
def get_tasks():
    cached = r.get('tasks_cache')
    if cached:
        return jsonify(json.loads(cached))
    tasks  = Task.query.all()
    result = [{'id': t.id, 'title': t.title, 'done': t.done} for t in tasks]
    r.setex('tasks_cache', 30, json.dumps(result))
    return jsonify(result)

@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    task = Task(title=data['title'])
    db.session.add(task)
    db.session.commit()
    r.delete('tasks_cache')
    return jsonify({'id': task.id, 'title': task.title}), 201

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    r.delete('tasks_cache')
    return jsonify({'message': 'Supprime'}), 200

@app.route('/health')
def health():
    visits = r.incr('visit_count')
    return jsonify({'status': 'ok', 'visits': visits})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
