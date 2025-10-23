del /a /f /s /q ..\common\proto\pb2\*_pb2.py

.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/any.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/common.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_base.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_interaction.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_leisure.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_login.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_match.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_player_vault.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/http_trade_center.proto

.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/ws_base.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/ws_beat.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/ws_leisure.proto
.\luck_proto\protoc_27_1 -I=./luck_proto --python_out=./common/proto/pb2/ ./luck_proto/ws_client.proto
pause

