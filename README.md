# PresencePi
Track how many people are present in a room using a laser sensor barrier attached to a Raspberry Pi counting people entering and leaving the room

## Pseudo HTTP queries to adjust the counter
### Get current people in the room
    curl -i -XPOST "http://presencepi:8086/query?db=presence" -H 'Authorization: Token user:passwd' --data-urlencode "q=SELECT "Presence" FROM "People" WHERE "MotionSensor" = 'Eingang' GROUP BY * ORDER BY DESC LIMIT 1"

### Increase current people in room by 1 + write control tag
    curl -i -XPOST "http://presencepi:8086/write?db=presence" -H 'Authorization: Token user:passwd' --data-binary 'People,MotionSensor=Eingang Presence=$(CURRENT_PEOPLE_IN_ROOM + 1)i,Cumulative=1i,Control=1i'

### Decrease current people in room by 1 + write control tag
    curl -i -XPOST "http://presencepi:8086/write?db=presence" -H 'Authorization: Token user:passwd' --data-binary 'People,MotionSensor=Eingang Presence=$(CURRENT_PEOPLE_IN_ROOM - 1)i,Control=-1i'

### Set current people in room to 0 + write control tag
    curl -i -XPOST "http://presencepi:8086/write?db=presence" -H 'Authorization: Token user:passwd' --data-binary 'People,MotionSensor=Eingang Presence=0i,Control=0i'

## Grafana dashboard example
![Grafana](https://github.com/bolausson/PresencePi/blob/master/grafana-dashboard.png?raw=true)

## Components used
* Raspberry Pi 3b
* Photoresistor GL5516 on light sensor module LM393
* Laserdiode module 15 * 6 mm, 5 V
* some case

## Complet setup
![PresencePi_assembled-side-view](https://github.com/bolausson/PresencePi/blob/master/PresencePi_assembled-side-view.jpg?raw=true)
![PresencePi_assembled-top-view](https://github.com/bolausson/PresencePi/blob/master/PresencePi_assembled-top-view.jpg?raw=true)
![PresencePi_assembled-with-dashborad](https://github.com/bolausson/PresencePi/blob/master/PresencePi_assembled-with-dashborad.jpg?raw=true)
![PresencePi_installed-in-final-location](https://github.com/bolausson/PresencePi/blob/master/PresencePi_installed-in-final-location.jpg?raw=true)
