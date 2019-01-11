# openHAB Google Actions Bridge

https://developers.google.com/actions/smarthome/create

```
docker create \
 --name openhab-gabridge \
 --hostname openhab-gabridge \
 -v /home/user/gabridge.yaml:/app/config.yaml \
 -e CLIENTID=secret-id \
 --restart always \
 004helix/openhab-gabridge
```

1. Modify config.yaml
2. Proxy from internet using https
3. Create new project in Actions on Google
