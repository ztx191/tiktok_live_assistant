import json

from flask import Flask, jsonify, request, render_template
from src.service.question_management.manager import QuestionManager


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

class QuestionProcess:
    manager_service = QuestionManager()

    @classmethod
    def get_problems(cls):
        qa_path = r"../datas/新增问题和答案.json"
        with open(qa_path, "r", encoding="utf-8") as f:
            qa_list = json.load(f)
        return cls.manager_service.get_new_and_old_question(qa_list, "问题合并测试")


db = QuestionProcess()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/problems', methods=['GET'])
def get_problems():
    return jsonify(db.get_problems())




if __name__ == '__main__':
    app.run()
