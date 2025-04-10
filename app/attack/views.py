# -*— coding:utf-8 -*—
from bson import json_util
# flask框架 所需包
from flask import render_template, request, session, redirect, url_for, abort, flash, json, jsonify, Response

# LLM attack 所需包
from . import attack
from .deepinception.deepinception import deep_inception
from .jailbreakingllm.jailbreakingllm import jailbreakingllm
from .renellm.renellm import renellm
from .codechameleon.codechameleon import codechameleon
from .sap.sap import sap

# flask 数据库 所需包
from app.models import AttackParameter
from datetime import datetime

from .. import mongo


# 获取 目标大模型 黑盒攻击结果
@attack.route('/api/attack',methods=['GET','POST'])
# @login_required 暂时不需要用户登录
def _attack():
    # 获取前端发送的JSON数据
    data = request.get_json()

    # 验证必要字段是否存在 : (username 用户名 || attack_method 攻击方法 || attack_model 目标模型 || malicious_question_set 有害问题数据集)
    required_fields = ['username','attack_method','attack_model',"malicious_question_set"]
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # 获取系统时间,生成用户登录ID
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = data['username']
    id = username+'_'+formatted_time

    global malicious_question_set, result
    # 根据攻击方法获得对应有害数据集
    if data['attack_method'] == "renellm" and data["malicious_question_set"] == "advbench" :
        malicious_question_set = "app/data/renellm/advbench/harmful_behaviors_test.csv"
    elif data['attack_method'] == "codechameleon" and data["malicious_question_set"] == "advbench" :
        malicious_question_set = "app/data/codechameleon/all_problem_test.csv"
    elif data['attack_method'] == "deepinception" and data["malicious_question_set"] == "advbench" :
        malicious_question_set = "app/data/deepinception/"
    elif data['attack_method'] == "jailbreakingllm" and data["malicious_question_set"] == "advbench" :
        malicious_question_set = "app/data/jailbreakingllm/all_problem_test.csv"
    elif data['attack_method'] == "sap" and data["malicious_question_set"] == "advbench" :
        malicious_question_set = "app/data/sap/all_problem_test.csv"


    # 创建AttackRecord对象并赋值
    attack_parameter = AttackParameter()

    attack_parameter.id = id
    attack_parameter.time = formatted_time
    attack_parameter.username = username
    attack_parameter.attack_method = data['attack_method']
    attack_parameter.malicious_question_set = malicious_question_set
    attack_parameter.attack_model = data['attack_model']
    attack_parameter.retry_times = 10
    attack_parameter.prompt = data['prompt']

    # 处理后端逻辑,目前可以选择五种攻击方法
    if data["attack_method"] == "renellm" :
        result = renellm(attack_parameter)
    elif  data["attack_method"] == "codechameleon" :
        result = codechameleon(attack_parameter)
    elif data["attack_method"] == "deepinception" :
        result = deep_inception(attack_parameter)
    elif data["attack_method"] == "jailbreakingllm":
        result = jailbreakingllm(attack_parameter)
    elif data["attack_method"] == "sap":
        result = sap(attack_parameter)

    return jsonify(result)


# 获取用户历史记录
@attack.route('/api/history',methods=['GET','POST'])
# @login_required 暂时不需要用户登录
def get_history_by_username():
    data = request.get_json()
    username = data["username"]

    attack_results_collection = mongo.db.attack_results
    attack_results_documents = list(attack_results_collection.find(
        {"username": username},
        {"results": 0}
    ))

    return_data = json_util.dumps(attack_results_documents)
    return return_data

@attack.route('/api/history/details',methods=['GET','POST'])
# @login_required 暂时不需要用户登录
def get_history_details_by_attack_id():
    data = request.get_json()
    attack_id = data["attack_id"]

    attack_results_collection = mongo.db.attack_results
    attack_results_document = attack_results_collection.find_one(
        {"attack_id": attack_id},
    )

    return_data = json_util.dumps(attack_results_document)
    return return_data
