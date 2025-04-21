import json
import pandas as pd


# 读取JSON数据
def convert_json_to_excel(json_data, output_file):
    # 解析JSON数据
    data = json.loads(json_data)

    # 创建一个空列表存储所有问答对
    qa_pairs = []

    # 遍历JSON数组提取问答对
    for group in data:
        for qa in group:
            qa_pairs.append({
                "问题": qa["问题"],
                "答案": qa["答案"]
            })

    # 创建DataFrame
    df = pd.DataFrame(qa_pairs)

    # 保存为Excel文件
    df.to_excel(output_file, index=False)
    print(f"Excel文件已保存为: {output_file}")


# JSON字符串(这里用...代替原始的长JSON字符串)
with open("./datas/新增问题&答案.json", "r", encoding="utf-8") as f:
    json_str = f.read()

# 调用函数转换并保存
convert_json_to_excel(json_str, "qa_list.xlsx")
