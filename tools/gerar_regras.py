# -*- coding: utf-8 -*-
"""Gera firebase-rules.json (v7). Expressões repetidas ficam em variáveis para não haver erro de digitação."""
import json
S = "auth != null && root.child('staff').child(auth.uid).child('active').val() === true"
G = S + " && root.child('staff').child(auth.uid).child('role').val() === 'Gerente'"
def ACC(m='$mesa'):
    return ("root.child('mesa_sid').child(%s).exists() && root.child('acessos').child(root.child('mesa_sid').child(%s).val()).child(auth.uid).val() === true" % (m, m))
STR = lambda n: "newData.isString() && newData.val().length <= %d" % n
NUM = "newData.isNumber()"
SID_RE = "/^s[a-z0-9]{10,40}$/"
PUSH_RE = "/^-[A-Za-z0-9_-]{15,25}$/"
OTHER_NO = {".validate": False}

rules = {
 ".read": False, ".write": False,

 "staff": {
  ".read": G,
  "$uid": {
   ".read": "auth != null && auth.uid === $uid",
   ".write": G,
   ".validate": "newData.hasChildren(['name','role','active'])",
   "name": {".validate": STR(80)},
   "email": {".validate": STR(120)},
   "role": {".validate": "newData.isString() && (newData.val() === 'Gerente' || newData.val() === 'Garçom' || newData.val() === 'Cozinheiro' || newData.val() === 'Caixa')"},
   "active": {".validate": "newData.isBoolean()"},
   "allowedTabs": {"$i": {".validate": STR(20)}},
   "mustChangePassword": {".write": "auth != null && auth.uid === $uid && newData.val() === false", ".validate": "newData.isBoolean()"},
   "createdAt": {".validate": NUM},
   "createdBy": {".validate": STR(80)},
   "$other": OTHER_NO
  }
 },

 "tables": {".read": S, ".write": S},

 # histórico de vendas: qualquer funcionário cria/atualiza; só o Gerente apaga
 "historico": {
  ".read": S,
  "$id": {".write": S + " && (newData.exists() || root.child('staff').child(auth.uid).child('role').val() === 'Gerente')"}
 },

 "chats_arquivo": {".read": S, ".write": S},

 # só o campo "ping" é público (app do cliente mostra "atendente em linha"); o nome do atendente fica só para a equipe
 "staff_presence": {
  ".read": S, ".write": S,
  "ping": {".read": "auth != null", ".validate": NUM},
  "agent": {".validate": STR(80)},
  "$other": OTHER_NO
 },

 "backups": {
  ".read": G,
  "$id": {
   ".write": "(" + G + ") || (" + S + " && !data.exists())",
   ".validate": "newData.child('app').val() === 'smartcomanda' && newData.hasChild('localStorage')"
  }
 },

 "exclusoes": {
  ".read": G,
  "$id": {
   ".write": S + " && !data.exists() && newData.exists() && newData.child('uid').val() === auth.uid",
   ".validate": "newData.hasChildren(['id','ts','tipo','uid'])"
  }
 },

 "mesa_sid": {".read": S, ".write": S},

 "sessoes": {
  "$sid": {".read": "auth != null", ".write": S}
 },

 "mesa_publica": {
  "$mesa": {
   ".read": "(" + S + ") || (auth != null && " + ACC() + ")",
   ".write": S
  }
 },

 "acessos": {
  "$sid": {
   "$uid": {
    ".read": "auth != null && (auth.uid === $uid || (" + S + "))",
    ".write": "(" + S + ") || (auth != null && auth.uid === $uid && newData.val() === true && $sid.matches(" + SID_RE + ") && root.child('sessoes').child($sid).child('status').val() === 'ocupada')",
    ".validate": "newData.isBoolean()"
   }
  }
 },

 "encomendas": {
  ".read": S, ".write": S,
  ".indexOn": ["whatsappDigits", "orderNumber", "sessionId"],
  "$id": {
   ".read": "auth != null && data.child('uid').val() === auth.uid",
   # cliente: só CRIA o próprio pedido, com status inicial, valor plausível e chave gerada pelo Firebase
   ".write": ("auth != null && !data.exists() && $id.matches(" + PUSH_RE + ") && newData.child('uid').val() === auth.uid"
              " && newData.child('sessionId').isString() && root.child('acessos').child(newData.child('sessionId').val()).child(auth.uid).val() === true"
              " && newData.child('status').val() === 'Recebida' && newData.child('totalValue').isNumber() && newData.child('totalValue').val() >= 0 && newData.child('totalValue').val() <= 20000"),
   "id": {".validate": NUM}, "orderNumber": {".validate": NUM},
   "orderCode": {".validate": STR(20)}, "client": {".validate": STR(120)},
   "sessionId": {".validate": STR(60)}, "uid": {".validate": STR(60)}, "mesa": {".validate": NUM},
   "whatsapp": {".validate": STR(40)}, "whatsappDigits": {".validate": STR(20)},
   "date": {".validate": STR(12)}, "time": {".validate": STR(8)}, "sector": {".validate": STR(60)},
   "status": {".validate": "newData.isString() && newData.val().length <= 30"},
   "itemsDescription": {".validate": STR(1600)},
   "totalValue": {".validate": "newData.isNumber() && newData.val() >= 0 && newData.val() <= 1000000"},
   "extraValue": {".validate": NUM}, "createdAt": {".validate": STR(40)},
   "itemsList": {"$i": {
      "id": {".validate": "(newData.isString() && newData.val().length <= 40) || newData.isNumber()"},
      "name": {".validate": STR(160)},
      "qty": {".validate": "newData.isNumber() && newData.val() >= 0 && newData.val() <= 1000"},
      "price": {".validate": "newData.isNumber() && newData.val() >= 0 && newData.val() <= 100000"},
      "$other": {".validate": "(newData.isString() && newData.val().length <= 100) || newData.isNumber() || newData.isBoolean()"}
   }},
   "$other": {".validate": "(newData.isString() && newData.val().length <= 200) || newData.isNumber() || newData.isBoolean()"}
  }
 },

 # contador PEDIDO:NN — o cliente só consegue somar +1 (limitação conhecida: ver RELATORIO-SEGURANCA.md)
 "contadores": {
  ".read": "auth != null",
  ".write": S,
  "encomenda": {".write": "auth != null && newData.isNumber() && newData.val() <= 1000000 && newData.val() === (data.exists() ? data.val() + 1 : 1)"}
 },

 "chats": {
  ".read": S, ".write": S,
  "$mesa": {
   ".read": "auth != null && " + ACC(),
   "$msg": {
    ".write": "auth != null && " + ACC() + " && !data.exists() && $msg.matches(" + PUSH_RE + ") && newData.child('sender').val() === 'cliente'",
    ".validate": "newData.hasChildren(['sender','text','timestamp'])",
    "sender": {".validate": "newData.val() === 'cliente' || newData.val() === 'atendente'"},
    "text": {".validate": "newData.isString() && newData.val().length >= 1 && newData.val().length <= 500"},
    "timestamp": {".validate": NUM}, "table": {".validate": NUM},
    "time": {".validate": STR(12)}, "clientName": {".validate": STR(80)},
    "agent": {".validate": STR(80)}, "kind": {".validate": STR(20)},
    "$other": OTHER_NO
   }
  }
 },

 "chat_meta": {
  ".read": S, ".write": S,
  "$mesa": {
   ".read": "auth != null && " + ACC(),
   "clientPing": {".write": "auth != null && " + ACC(), ".validate": NUM},
   "clientReadUpTo": {".write": "auth != null && " + ACC(), ".validate": NUM},
   "clientTyping": {".write": "auth != null && " + ACC(), ".validate": NUM},
   "staffTyping": {".validate": NUM}, "staffReadUpTo": {".validate": NUM}, "agent": {".validate": STR(80)},
   "$other": OTHER_NO
  }
 },

 # pedido de "Finalizar" feito pelo celular: precisa trazer a sessão (sid) ATUAL da mesa
 "finalizar_pedidos": {
  ".read": S, ".write": S,
  "$mesa": {
   ".read": "auth != null && " + ACC(),
   ".write": "auth != null && " + ACC(),
   ".validate": "newData.hasChildren(['mesa','sid','ts']) && newData.child('sid').val() === root.child('mesa_sid').child($mesa).val()",
   "mesa": {".validate": NUM}, "sid": {".validate": STR(60)}, "client": {".validate": STR(80)},
   "total": {".validate": NUM}, "ts": {".validate": NUM},
   "source": {".validate": "newData.val() === 'celular'"},
   "$other": OTHER_NO
  }
 },

 # avaliação: chave fixa por comanda (fbs_<sid>), criada uma única vez, só por quem pertence à comanda
 "feedbacks": {
  ".read": S, ".write": S,
  "$id": {
   ".write": ("auth != null && !data.exists() && newData.child('sid').isString() && $id === 'fbs_' + newData.child('sid').val()"
              " && root.child('acessos').child(newData.child('sid').val()).child(auth.uid).val() === true"),
   ".validate": "newData.hasChildren(['id','service','food'])",
   "id": {".validate": NUM}, "receivedAt": {".validate": NUM}, "sid": {".validate": STR(60)}, "table": {".validate": NUM},
   "client": {".validate": STR(120)},
   "service": {".validate": "newData.isNumber() && newData.val() >= 1 && newData.val() <= 5"},
   "food": {".validate": "newData.isNumber() && newData.val() >= 1 && newData.val() <= 5"},
   "total": {".validate": NUM}, "comment": {".validate": STR(600)}, "time": {".validate": STR(20)},
   "items": {"$i": {
      "id": {".validate": "(newData.isString() && newData.val().length <= 40) || newData.isNumber()"},
      "name": {".validate": STR(160)}, "qty": {".validate": NUM}, "price": {".validate": NUM}, "status": {".validate": STR(40)},
      "$other": {".validate": "(newData.isString() && newData.val().length <= 100) || newData.isNumber() || newData.isBoolean()"}
   }},
   "$other": {".validate": "(newData.isString() && newData.val().length <= 200) || newData.isNumber() || newData.isBoolean()"}
  }
 },

 # marcador "esta comanda já foi avaliada": o cliente só CRIA (nunca apaga nem troca)
 "avaliacoes_sessao": {
  ".read": S, ".write": S,
  "$sid": {
   ".read": "auth != null && root.child('acessos').child($sid).child(auth.uid).val() === true",
   ".write": "auth != null && root.child('acessos').child($sid).child(auth.uid).val() === true && !data.exists() && newData.exists()",
   "id": {".validate": NUM}, "service": {".validate": NUM}, "food": {".validate": NUM}, "ts": {".validate": NUM},
   "$other": OTHER_NO
  }
 }
}
json.dump({"rules": rules}, open('build/firebase-rules.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('regras geradas')
