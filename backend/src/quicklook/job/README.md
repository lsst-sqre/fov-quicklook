# Job

* Job is the unit of processing within the quicklook generation pipeline.
  * Used only within the pipeline.
* Instance is created only when quicklook generation is requested
* Holds information needed to determine processing target and priority within the pipeline.
* Holds the following information:
  * Processing target visit
  * uuid
  * Information for determining priority:
    * waiting_users
      * How many users are waiting for this visit
    * seq
      * Sequential number when instance was created
* Jobs with `waiting_users <= 0` are skipped when entering each stage.
* `__new__`
  * Only one is created per visit
