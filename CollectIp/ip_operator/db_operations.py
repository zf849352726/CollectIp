import pymysql
from config import DB_CONFIG

class DatabaseOperator:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise

    def disconnect(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_ip_pool(self):
        """获取IP池数据"""
        try:
            self.connect()
            sql = "SELECT server, score FROM index_ipdata"
            self.cursor.execute(sql)
            return self.cursor.fetchall()
        finally:
            self.disconnect()

    def update_ip_score(self, server, score):
        """更新IP分数，如果分数低于80则删除该IP"""
        try:
            self.connect()
            if score < 10:
                # 分数低于10，直接删除该IP记录
                sql = "DELETE FROM index_ipdata WHERE server = %s"
                self.cursor.execute(sql, (server,))
            else:
                # 分数大于等于10，更新分数
                sql = "UPDATE index_ipdata SET score = %s WHERE server = %s"
                self.cursor.execute(sql, (score, server))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"更新/删除IP失败: {e}")
            raise
        finally:
            self.disconnect() 