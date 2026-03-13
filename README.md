# 关于规范（必读）

**项目不是一个人的，请遵守规范。**

1. 参与项目前请认真阅读每个目录下的功能，充分理解项目后再编写代码。
2. 这里不需要重复代码，如果有多次需要调用的某个相同段落的代码，请封装好。
3. 如果有封装好的正好你又需要的代码（工具）时，请不要不好意思，那就是分享给你用的。
4. 请注意命名规范，尽量或必须使用英文，不会的请使用翻译工具。
5. 一时爽 or 一直爽，这是个问题。这里不欢迎一时爽写出来的代码，请经过考虑后再编写，并且在将来认为有更好的实现方法时进行持续优化。
6. 无论你是从面向过程或面向对象过来的，请不要争执，本质都是组合，每门语言都有其优点的地方，不存在谁牛逼不牛逼，问问自己用得如何。
7. 项目中不需要：已经不需要的代码，如果确实需要留下，请注释详情信息以及为何留下。最佳做法就是当场解决。请不要出现：v2、new什么的与旧代码相似度非常高的代码。



# 项目目录介绍

* `c_services` 该目录下表示所有子服务
* `common` 该目录下表示所有的工具包，及其它目录公共使用的如：常量、消息体、公共基类等
* `lucky_game`：该目录是web接口，所有的表定义在该目录下
* `lucky_ws`：该目录是`ws`服务
* `lucky_proto`：该目录是所有`protobuf`协议文件（生成代码在common/proto/目录下）

# 项目依赖

* python：3.11.8
* mysql：8.0
* redis：7.x
* rabbitmq：3.13.2

# 关于ws协议

## 完整消息

命令号占用字节数（长度） + 命令号 + body

~~~ protobuf
// http: 返回基础模型
message S2CBase {
    uint32 code = 1;
    optional google.protobuf.Any data = 2;  // 可选
    string msg = 3;
}

// ws 子服务返回基础类型 c -> child
message S2CcService {
    uint32 code = 1;
    optional google.protobuf.Any data = 2;
    string hint = 3;  // 提示
}
~~~

# 关于nsanic包安装
pip uninstall nsanic
pip install nsanic --index-url https://__token__:gldt-xfzc6gpYV6gHVfCV6G_Z@git.leqiku.com/api/v4/projects/135/packages/pypi/simple



# 关于数据迁移

数据迁移工具采用与`tortoise-orm`配套的`aerich`迁移工具

1. 在`model`下对应的服务目录下定义好数据模型
   `model_db/main.py --> class SysAccount(Model)`:
2. 将数据模型所在的文件名添加到配置下的 MODEL_LIST内
   MODEL_LIST = [sys_account]
3. 将数据库配置单独初始化到`config/__init__.py`内(已添加过的忽略这一步)
   `migrate_db = conf_srv.db_migration`(`db_migration`对应当前项目可迁移的库模型)
4. 进入项目根目录，执行 `aerich init -t lucky_game.config.migrate_db `(对应在`__init__.py`中的名称) 初始化数据库连接，同一数据库下只需做一次，更换服务数据库需要从该步骤重新开始执行，在同一数据库服务下，更新或回退，只参照5、6、7步骤
5. 再执行 `aerich init-db` 初始化数据库结构
6. `aerich migrate` 生成迁移数据（修改了模型类（Model）或者模型字段（Field）后，需要生成迁移文件。）
7. `aerich upgrade` 发起迁移（应用迁移）
8. 如有需求需要回退上一个版本执行 `aerich downgrade`

## 详细操作

1. 打开命令行，切换到项目根目录

2. 初始化配置项

  `aerich init -t db.config.TORTOISE_ORM`

  初始化完成后会在当前目录生成一个文件`pyproject.toml`和一个文件夹`migrations`

  * `pyproject.toml`: 保存配置文件路径
  * `migrations`：存放`.sql`迁移文件 

3. 初始化数据库，一般情况下只用一次

  `aerich init-db`

  * 如果`TORTOISE_ORM`配置文件中的models改了名，执行这条命令时需要增加`--app`参数，来指定你修改的名字。
  *  在migrations的指定`app`目录下生成`sql`文件（如果model不为空时），并在数据库中生成表。

4. 更新模型并进行迁移

  `aerich migrate --name any_name`

  * 每次修改model后执行此命令，将在migrations文件夹下生成`.sql`迁移文件；
  * `--name`参数为你的迁移文件添加备注，默认为update；
  * 迁移文件名的格式为`{version_num}{datetime}{any_name|update}.sql`；
  * 如果`aerich`识别到您正在重命名列，它会要求重命名`{old_column}`为`{new_column}` [True]，您可以选择True
       重命名列而不删除列，或者选择False删除列然后创建，如果使用`Mysql`，只有8.0+支持重命名。

5. 更新最新修改到数据库

  `aerich upgrade [xxx.sql]`

6. 后续每次修改models文件内容（新增、删除或修改数据模型， 非models文件重命名），只需执行步骤4、5即可。

7. 其它操作

* 降级到指定版本
     `aerich downgrade -v` 指定版本 -d` 降级的同时删除迁移文件 `--yes` 确认删除，不再交互式输入
* 显示当前可以迁移的版本
     `aerich heads`
* 显示迁移历史
     `aerich history`

8. 查看数据库，验证迁移操作。



## Restore `aerich` workflow （还原`aerich`工作流）

In some cases, such as broken changes from upgrade of `aerich`, you can't run `aerich migrate` or `aerich upgrade`, you can make the following steps（在某些情况下，比如从`aerich `的升级破碎的更改，你不能运行`aerich migrate` 或 `aerich upgrade`，你可以做以下步骤:）:

1. drop `aerich` table. - 删除 `aerich`表
2. delete `migrations/{app}` directory. - 删除migrations/ 下的对应文件夹
3. rerun `aerich init-db`. - 再次运行该命令

Note that these actions is safe, also you can do that to reset your migrations if your migration files is too many.

请注意，这些操作是安全的，如果迁移文件太多，您也可以这样做来重置迁移。

改工作流只是建表，如果数据库有表则不新建，如果对表已经有修改则需要进一步迁移



## `sql`

~~~ mysql
# 修改自增起始值
ALTER TABLE my_table AUTO_INCREMENT = 100000;
~~~



# 关于`protobuf`

`proto`文件全部定义在`promising_proto`目录下

* `http`
* `ws`

~~~ protobuf
// 通过-I或--proto_path选项来指定额外的搜索路径。
 ./luck_proto/protoc_27_1.exe -I=luck_proto --python_out=common/proto/pb2 luck_proto/common.proto
~~~



## 规范

### 文件命定义

* `ws_xxx.proto`
* `http`暂不用前缀

### 消息体

* 服务端下发

  ~~~ protobuf
  message S2CXxx {
  	...
  }
  ~~~

* 客户端请求

  ~~~ protobuf
  message C2SXxx {
  	...
  }
  ~~~

* 双方都用

  ~~~ protobuf
  message PubSCXxx {
  	...
  }
  ~~~



## 关于`Any`

https://github.com/protocolbuffers/protobuf/releases

从此处下载的压缩包里面包含得有




# 命名规范

## 1.类名

* 驼峰体

  ~~~ python
  class TestClass
  ~~~

## 2.常量名

* 大写 + `_`

  ~~~ python
  TEST_CONST
  ~~~

### 3.变量名

* 小写 + `_`

  ~~~ python
  test_count
  ~~~
 
## 依赖与版本管理

* 已存在的 Pip 依赖版本不得随意修改（升级/降级），除非：
  * 有明确需求说明和影响评估（兼容性、风险、回滚方案）
  * 在变更记录中写明修改理由与验证方式
* 新增依赖时应明确版本号或采用上游建议的稳定版本，避免不锁版本带来的不可控安装结果
* 安装依赖必须使用项目的 requirement.txt，不允许本地或 CI 中私自覆盖版本
* 如需调整版本，请在提交说明中标注“依赖版本变更”并附测试验证结论
