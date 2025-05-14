del /a /f /s /q ..\common\proto\pb2\*_pb2.py

.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/any.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/common.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_base.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_interaction.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_leisure.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_login.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_match.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_player_vault.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/http_trade_center.proto

.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/ws_base.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/ws_beat.proto
.\promising_proto\protoc_27_1 -I=./promising_proto --python_out=./common/proto/pb2/ ./promising_proto/ws_leisure.proto
pause

