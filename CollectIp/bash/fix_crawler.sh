#!/bin/bash

# ==============================================================================
# 脚本名称: fix_crawler.sh
# 描述: 修复爬虫模块中的编码问题并重启相关服务
# 作者: 系统维护人员
# 日期: 2023-12-01
# ==============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 激活虚拟环境
VENV_PATH="/usr/local/venv/djangoLearn/bin/activate"
if [ -f "$VENV_PATH" ]; then
    log_info "正在激活虚拟环境: $VENV_PATH"
    source "$VENV_PATH"
else
    log_warn "虚拟环境文件不存在: $VENV_PATH"
    log_warn "继续执行，但可能会出现Python环境问题"
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
log_info "脚本目录: $SCRIPT_DIR"

# 确定项目根目录
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"
log_info "项目根目录: $PROJECT_ROOT"

# 切换到项目根目录
cd "$PROJECT_ROOT" || {
    log_error "无法切换到项目根目录: $PROJECT_ROOT"
    exit 1
}

# 检查爬虫模块目录是否存在
CRAWLER_DIR="$PROJECT_ROOT/ip_operator/services"
if [ ! -d "$CRAWLER_DIR" ]; then
    log_error "爬虫模块目录不存在: $CRAWLER_DIR"
    exit 1
fi

# 备份原始文件
CRAWLER_FILE="$CRAWLER_DIR/crawler.py"
BACKUP_FILE="$CRAWLER_DIR/crawler.py.bak_$(date +%Y%m%d%H%M%S)"

if [ -f "$CRAWLER_FILE" ]; then
    log_info "备份爬虫文件: $CRAWLER_FILE -> $BACKUP_FILE"
    cp "$CRAWLER_FILE" "$BACKUP_FILE" || {
        log_error "备份文件失败"
        exit 1
    }
else
    log_error "爬虫文件不存在: $CRAWLER_FILE"
    exit 1
fi

# 检查文件编码
log_info "检查文件编码..."
FILE_ENCODING=$(file -bi "$CRAWLER_FILE" | awk -F"=" '{print $2}')
log_info "文件编码: $FILE_ENCODING"

# 如果不是UTF-8，转换为UTF-8
if [[ "$FILE_ENCODING" != "utf-8" && "$FILE_ENCODING" != "utf8" ]]; then
    log_warn "文件不是UTF-8编码，尝试转换..."
    iconv -f "$FILE_ENCODING" -t utf-8 "$CRAWLER_FILE" > "$CRAWLER_FILE.utf8" && \
    mv "$CRAWLER_FILE.utf8" "$CRAWLER_FILE"
    
    if [ $? -eq 0 ]; then
        log_info "已将文件转换为UTF-8编码"
    else
        log_error "编码转换失败"
        exit 1
    fi
fi

# 检查是否存在Base64编码函数
log_info "检查爬虫文件是否包含Base64编码函数..."
if ! grep -q "def encode_movie_name" "$CRAWLER_FILE"; then
    log_info "未找到编码函数，添加Base64编码支持..."
    
    # 创建Python脚本来添加函数
    TMP_SCRIPT="/tmp/add_encode_function.py"
    cat > "$TMP_SCRIPT" << 'EOF'
import re
import sys

# 读取文件
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

# 导入模块部分
if 'import base64' not in content:
    # 找到最后一个import语句
    import_match = re.search(r'^import .*$', content, re.MULTILINE)
    if import_match:
        # 在最后一个import之后添加base64导入
        pos = import_match.end()
        content = content[:pos] + '\nimport base64' + content[pos:]
    else:
        # 如果没有找到import语句，在文件开头添加
        content = 'import base64\n' + content

# 添加编码函数
if 'def encode_movie_name' not in content:
    encode_function = '''
def encode_movie_name(movie_name):
    """将电影名称编码为Base64以处理中文字符"""
    if not movie_name:
        return None
    try:
        return base64.b64encode(movie_name.encode('utf-8')).decode('ascii')
    except Exception as e:
        logging.error(f"编码电影名称时出错: {e}")
        return None

def decode_movie_name(encoded_name):
    """从Base64解码电影名称"""
    if not encoded_name:
        return None
    try:
        return base64.b64decode(encoded_name).decode('utf-8')
    except Exception as e:
        logging.error(f"解码电影名称时出错: {e}")
        return None
'''
    # 寻找合适的位置添加函数
    # 在第一个函数定义之前添加
    func_match = re.search(r'^def ', content, re.MULTILINE)
    if func_match:
        pos = func_match.start()
        content = content[:pos] + encode_function + '\n' + content[pos:]
    else:
        # 如果没有找到函数定义，添加到文件末尾
        content += '\n' + encode_function

# 写回文件
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(content)
EOF

    # 执行Python脚本
    python "$TMP_SCRIPT" "$CRAWLER_FILE"
    
    if [ $? -eq 0 ]; then
        log_info "已添加Base64编码函数"
    else
        log_error "添加编码函数失败"
        exit 1
    fi
else
    log_info "已存在Base64编码函数，无需添加"
fi

# 检查是否存在run_spider_process函数
log_info "检查爬虫文件是否包含run_spider_process函数..."
if ! grep -q "def run_spider_process" "$CRAWLER_FILE"; then
    log_info "未找到run_spider_process函数，添加函数..."
    
    # 创建Python脚本来添加函数
    TMP_SCRIPT="/tmp/add_spider_process_function.py"
    cat > "$TMP_SCRIPT" << 'EOF'
import re
import sys

# 读取文件
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

# 添加run_spider_process函数
if 'def run_spider_process' not in content:
    spider_process_function = '''
def run_spider_process(spider_name, movie_name=None, spider_settings=None, crawl_config=None):
    """在子进程中运行爬虫
    
    Args:
        spider_name: 爬虫名称
        movie_name: 电影名称(可选)
        spider_settings: 爬虫设置(可选)
        crawl_config: 爬取配置(可选)
    
    Returns:
        bool: 是否成功启动爬虫进程
    """
    import os
    import sys
    import json
    import logging
    import importlib
    
    try:
        # 设置环境变量
        if movie_name:
            # 对电影名称进行编码，处理中文字符
            encoded_name = encode_movie_name(movie_name)
            if encoded_name:
                os.environ['MOVIE_NAME_ENCODED'] = encoded_name
                logging.info(f"设置电影名称(编码): {encoded_name}")
            else:
                logging.error(f"无法编码电影名称: {movie_name}")
                
            # 同时设置未编码的名称作为备份
            os.environ['MOVIE_NAME'] = movie_name
            logging.info(f"设置电影名称: {movie_name}")
            
        # 设置爬虫配置
        if crawl_config:
            try:
                if isinstance(crawl_config, dict):
                    crawl_config_str = json.dumps(crawl_config)
                    os.environ['CRAWL_CONFIG'] = crawl_config_str
                    logging.info(f"设置爬虫配置: {crawl_config_str}")
                else:
                    logging.warning(f"爬虫配置不是字典: {type(crawl_config)}")
            except Exception as e:
                logging.error(f"设置爬虫配置失败: {e}")
        
        # 设置爬虫设置
        if spider_settings:
            try:
                if isinstance(spider_settings, dict):
                    settings_str = json.dumps(spider_settings)
                    os.environ['SPIDER_SETTINGS'] = settings_str
                    logging.info(f"设置爬虫设置: {settings_str}")
                else:
                    logging.warning(f"爬虫设置不是字典: {type(spider_settings)}")
            except Exception as e:
                logging.error(f"设置爬虫设置失败: {e}")
        
        # 导入爬虫模块
        logging.info(f"导入爬虫模块: {spider_name}")
        
        # 根据爬虫名称选择不同的导入路径
        if spider_name == 'douban':
            # 导入豆瓣爬虫
            from ip_operator.crawl_ip.crawl_ip.spiders.douban_spider import DoubanSpider
            spider_class = DoubanSpider
        elif spider_name == 'collectip':
            # 导入IP爬虫
            from ip_operator.crawl_ip.crawl_ip.spiders.collectip_spider import CollectIpSpider
            spider_class = CollectIpSpider
        else:
            logging.error(f"未知的爬虫名称: {spider_name}")
            return False
        
        # 导入Scrapy相关模块
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        
        # 获取爬虫设置
        settings = get_project_settings()
        
        # 创建爬虫进程
        process = CrawlerProcess(settings)
        
        # 添加爬虫
        process.crawl(spider_class)
        
        # 启动爬虫
        logging.info(f"启动爬虫: {spider_name}")
        process.start()
        
        logging.info(f"爬虫 {spider_name} 执行完成")
        return True
        
    except ImportError as e:
        logging.error(f"导入模块失败: {e}")
        return False
    except Exception as e:
        logging.error(f"运行爬虫进程时出错: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False
'''
    
    # 寻找合适的位置添加函数
    # 在start_douban_crawl函数之前添加
    func_match = re.search(r'^def start_douban_crawl', content, re.MULTILINE)
    if func_match:
        pos = func_match.start()
        content = content[:pos] + spider_process_function + '\n\n' + content[pos:]
    else:
        # 如果没有找到函数定义，添加到文件末尾
        content += '\n' + spider_process_function

    # 写回文件
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        f.write(content)
EOF

    # 执行Python脚本
    python "$TMP_SCRIPT" "$CRAWLER_FILE"
    
    if [ $? -eq 0 ]; then
        log_info "已添加run_spider_process函数"
    else
        log_error "添加run_spider_process函数失败"
        exit 1
    fi
else
    log_info "已存在run_spider_process函数，无需添加"
fi

# 检查start_douban_crawl函数是否正确使用编码
log_info "检查start_douban_crawl函数是否正确使用编码..."
if ! grep -q "encode_movie_name" "$CRAWLER_FILE"; then
    log_info "更新start_douban_crawl函数，添加编码支持..."
    
    # 创建Python脚本来更新函数
    TMP_SCRIPT="/tmp/update_start_douban_crawl.py"
    cat > "$TMP_SCRIPT" << 'EOF'
import re
import sys

# 读取文件
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

# 更新start_douban_crawl函数
start_douban_pattern = r'def start_douban_crawl\([^)]*\):\s*"""[^"]*"""\s*try:\s*[^#]*?os\.environ\[\'MOVIE_NAME\'\]\s*=\s*movie_name'
replacement = '''def start_douban_crawl(movie_name, strategy="sequential", max_pages=1):
    """启动豆瓣爬虫
    
    Args:
        movie_name: 电影名称
        strategy: 爬取策略
        max_pages: 最大爬取页数
        
    Returns:
        bool: 是否成功启动爬虫
    """
    try:
        # 对电影名称进行编码，处理中文字符
        encoded_name = encode_movie_name(movie_name)
        if encoded_name:
            os.environ['MOVIE_NAME_ENCODED'] = encoded_name
            logging.info(f"设置电影名称(编码): {encoded_name}")
        else:
            logging.error(f"无法编码电影名称: {movie_name}")
            return False
            
        # 同时设置未编码的名称作为备份
        os.environ['MOVIE_NAME'] = movie_name'''

updated_content = re.sub(start_douban_pattern, replacement, content, flags=re.DOTALL)

# 写回文件
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(updated_content)
EOF

    # 执行Python脚本
    python "$TMP_SCRIPT" "$CRAWLER_FILE"
    
    if [ $? -eq 0 ]; then
        log_info "已更新start_douban_crawl函数"
    else
        log_error "更新start_douban_crawl函数失败"
    fi
else
    log_info "start_douban_crawl函数已经正确使用编码函数，无需更新"
fi

# 重启服务
log_info "修复完成，准备重启服务..."

# 检查是否存在Apache配置
if [ -f "/etc/apache2/apache2.conf" ]; then
    log_info "重启Apache服务..."
    sudo systemctl restart apache2 || {
        log_warn "无法重启Apache服务，可能需要手动重启"
    }
else
    log_warn "未找到Apache配置，跳过重启"
fi

# 测试爬虫功能
log_info "测试爬虫功能..."
if [ -f "$PROJECT_ROOT/CollectIp/ulits/test_crawler.py" ]; then
    log_info "执行爬虫测试脚本..."
    python "$PROJECT_ROOT/CollectIp/ulits/test_crawler.py" --type logs
else
    log_warn "未找到测试脚本，跳过测试"
fi

log_info "修复脚本执行完成！"
log_info "请检查日志确认爬虫功能是否正常"
exit 0 