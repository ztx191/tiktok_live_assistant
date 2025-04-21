from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

class QuestionManager:
    def __init__(self):
        self.questions = []  # 存储已有问题
        self.vectorizer = TfidfVectorizer()  # 用于文本向量化

    def add_questions(self, new_questions: List[str]):
        """批量添加新问题并进行合并"""
        if not self.questions:
            # 如果问题库为空，直接添加所有新问题
            self.questions.extend(new_questions)
            return

        # 对已有问题进行向量化
        existing_vectors = self.vectorizer.fit_transform(self.questions)

        for new_question in new_questions:
            # 将新问题转换为向量
            new_vector = self.vectorizer.transform([new_question])

            # 计算新问题与所有已有问题的相似度
            similarities = cosine_similarity(new_vector, existing_vectors)[0]

            # 找到最大相似度及其索引
            max_similarity = np.max(similarities)
            max_similarity_idx = np.argmax(similarities)

            if max_similarity > 0.85:
                # 如果相似度大于0.85，替换最相似的问题
                self.questions[max_similarity_idx] = new_question
            else:
                # 否则将新问题添加到问题库
                self.questions.append(new_question)

            # 更新向量化器
            existing_vectors = self.vectorizer.fit_transform(self.questions)

    def get_questions(self) -> List[str]:
        """获取当前所有问题"""
        return self.questions


def main():
    # 创建问题管理器实例
    manager = QuestionManager()

    # 添加一些初始问题
    initial_questions = [
        "如何使用Python进行文件操作？",
        "Python中的列表和元组有什么区别？",
        "什么是Python装饰器？"
    ]
    manager.add_questions(initial_questions)

    # 添加新问题
    new_questions = [
        "怎样用Python操作文件？",  # 与第一个问题相似
        "Python中如何处理异常？",  # 新问题
        "Python装饰器的用法是什么？"  # 与第三个问题相似
    ]
    manager.add_questions(new_questions)

    # 打印最终的问题列表
    print("最终问题列表：")
    for idx, question in enumerate(manager.get_questions(), 1):
        print(f"{idx}. {question}")


if __name__ == "__main__":
    main()




