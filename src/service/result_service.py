import json
import logging
import re

import jsonpath

logger = logging.getLogger(__name__)

# 使用正则表达式匹配 JSON 部分
json_pattern = re.compile(r'```json\n(.*?)\n```', re.DOTALL)


def extract_tool_call_arguments(llm_result):
    result = {}

    try:
        tool_calls_expr = '$.choices[0].message.tool_calls[0]'
        tool_calls = None
        try:
            tool_calls = jsonpath.search(tool_calls_expr, llm_result)
            tool_calls = tool_calls[0]
        except:
            pass

        arguments = None
        if tool_calls:
            arguments = tool_calls.get('function', {}).get('arguments')
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
        else:  # fix bug: newtouch
            content_expr = '$.choices[0].message.content'
            content = jsonpath.search(content_expr, llm_result)[0]

            content = content.replace("<tool_call>", "").replace("</tool_call>", "").strip()

            match = json_pattern.search(content)

            if match:
                content = match.group(1)
            else:
                content = "{}"

            try:
                arguments = json.loads(content)
                if 'arguments' in arguments:
                    arguments = arguments['arguments']
            except:
                try:
                    arguments = json.loads(content + '}')['arguments']
                except Exception as ex:
                    logger.error("extract tool call arguments error: %s", llm_result)

        result = arguments
        if isinstance(arguments, list):
            for argument in arguments:
                if isinstance(argument, str):
                    argument = json.loads(argument)
                if isinstance(argument, dict):
                    result.update(argument)
    except:
        pass

    return result


def response_clean(response_text):
    result = response_text
    result = result.replace("\t", "")
    result = result.replace("\\\\n", "\t")
    result = result.replace('\\n', '\n')
    result = result.replace('\\"', '"')
    result = result.replace('\t', '\\n')

    while result.find('\\\\') != -1:
        result = result.replace('\\\\', '\\')
    result = result.strip('"`\'').strip()
    return result


def get_json_data(text):
    """从文本中提取JSON数据"""
    pattern = r'```json\s*([\s\S]*?)\s*```'
    if isinstance(text, dict):
        text = text["choices"][-1]["message"]["content"]
    else:
        text = text.content
    if ("```json" not in text) and ("```" not in text):
        result = text
    else:
        match = re.search(pattern, text)
        if match:
            result = match.group(1)
        else:
            logger.error("模型未准确输出json格式文件！！！")
            return {}
    try:
        result = json.loads(result)

    except Exception as e:
        logger.error(f"提取json数据失败：{e}")
        return {}
    return result




if __name__ == '__main__':
    # import requests
    # import json
    #
    # url = "http://61.172.179.77:40004/claim-uat/api/mgr/claim/damage_amount"
    #
    # header = {
    #     "accept": "application/json",
    #     "Content-Type": "application/json"
    # }
    #
    # data = {
    #     "requestNo": "string",
    #     "requestTime": 0,
    #     "claim_type": "住院，住院津贴，身故",
    #     "claim_info": {},
    #     "claim_formula": "",
    #     "system_prompt": ""
    # }
    # result = requests.post(url=url, headers=header, data=json.dumps(data))
    # result = result.json()["data"]
    # print({"damage_info": result})
    content = '{"问题类型": "投保问题"}'
    _res = get_json_data(content)
    print(_res)


