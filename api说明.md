
API地址：https://app.walkingcode.com/API/kill-domains.php
以下是返回的格式，要取domains的数组里的网址用于屏蔽

{
    "code": 200,
    "message": "success",
    "data": {
        "domains": [
            "www.baidu.com",
            "www.163.com",
            "www.qq.com",
            "163.com"
        ],
        "total": 4,
        "list": [
            {
                "id": 1,
                "domain": "www.baidu.com",
                "status": 1,
                "created_at": "2025-12-27 11:14:07",
                "updated_at": "2025-12-27 11:14:07"
            },
            {
                "id": 2,
                "domain": "www.163.com",
                "status": 1,
                "created_at": "2025-12-27 11:14:08",
                "updated_at": "2025-12-27 11:25:40"
            },
            {
                "id": 3,
                "domain": "www.qq.com",
                "status": 1,
                "created_at": "2025-12-27 11:26:30",
                "updated_at": "2025-12-27 11:26:33"
            },
            {
                "id": 10,
                "domain": "163.com",
                "status": 1,
                "created_at": "2025-12-28 12:41:47",
                "updated_at": "2025-12-28 12:41:47"
            }
        ]
    },
    "timestamp": "2025-12-28 12:41:47"
}