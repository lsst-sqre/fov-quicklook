* stellarglobeの状態はreduxのstore
* store.dispatchによってのみ変更される
* store.dispatchはapp内から呼ばれることもPython-integrationから呼ばれることもある
* Pythonでもstoreのコピーを持っているが、これはstoreの状態を読むだけで、storeの状態を変更することはない
  * Pythonでコピーを持つのは、appとの接続が切れた後も復元できるようにするため
  * Python側で状態を参照するたびに毎回appと通信するのは非効率だろう
* storeに変更があった時にpatchをPythonにpushする
  * patchは順番が入れ替わったり届かないものがあるかもしれない
  * Pythonとapp双方でrevisionを保持しpatchにもrevisionを付け整合性を保つ
  