Here are the current configuration values.

* coordinator
  * replicas: 1
  * RAM: 256MB
  * CPU: 0.1 ~ 4 cores
* generator
  * replicas: 9
  * RAM: 32GB
  * CPU: 8 ~ 16 cores
* frontend
  * replicas: 4
  * RAM: 512MB
  * CPU: 0.1 ~ 2 cores
* db:
  * replicas: 1
  * RAM: 256MB
  * CPU: 0.1 ~ 2 cores
* object storage
  * capacity: 1TB
  * This storage is used to store data retrieved from butler after converting it to the format used by quicklook.
  * It is configured to store cache for 40 visits.

* CPU range represents requirement ~ limit.
* The generator and frontend can operate with fewer replicas.
* The generator's memory setting is set high because there seems to be a moment where it uses a large amount of memory (we haven't identified where yet) to prevent OOM Kill from occurring.