
API地址：https://app.walkingcode.com/API/kill-domains.php
以下是返回的格式，要取domains的数组里的网址用于屏蔽
password，是输出给客户端密码匹配的。

{
    "code": 200,
    "message": "success",
    "data": {
        "domains": [
            "www.qq.com",
            "www.163.com",
            "www.baidu.com"
        ],
        "total": 3,
        "list": [
            {
                "id": 3,
                "domain": "www.qq.com",
                "status": 1,
                "created_at": "2025-12-27 11:26:30",
                "updated_at": "2025-12-27 11:26:33"
            },
            {
                "id": 2,
                "domain": "www.163.com",
                "status": 1,
                "created_at": "2025-12-27 11:14:08",
                "updated_at": "2025-12-27 11:25:40"
            },
            {
                "id": 1,
                "domain": "www.baidu.com",
                "status": 1,
                "created_at": "2025-12-27 11:14:07",
                "updated_at": "2025-12-27 11:14:07"
            }
        ]
    },
    "password": "123",
    "timestamp": "2025-12-28 16:06:22"
}