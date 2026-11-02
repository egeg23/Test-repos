--!strict
--- Every string a player reads, in every launch locale.
---
--- A plain table rather than a LocalizationTable, because almost everything is
--- assembled at run time from numbers and names, and because a table can be
--- tested outside Roblox: tests/strings.spec.luau asserts every key exists in
--- all four locales with matching placeholders, and tools/check_hardcoded.py
--- asserts every key the code asks for is here.
---
--- The game's name lives in exactly one place: "brand.name" below.
---
--- Placeholders are positional, `{1}`, `{2}`, so a translator can move them.

local Strings = {}

export type Bundle = { ru: string, en: string, es: string, pt: string }

Strings.Fallback = "en"

Strings.Entries = {
	-- ---- brand ----
	["brand.name"] = {
		ru = "Сквиш-фабрика",
		en = "Squish Factory",
		es = "Fábrica de Squishies",
		pt = "Fábrica de Squishies",
	},
	["brand.tagline"] = {
		ru = "Собирай, сжимай, защищай",
		en = "Collect, squeeze, protect",
		es = "Colecciona, aprieta, protege",
		pt = "Coleciona, aperta, protege",
	},

	-- ---- common ----
	["common.close"] = {
		ru = "Закрыть",
		en = "Close",
		es = "Cerrar",
		pt = "Fechar",
	},
	["common.cancel"] = {
		ru = "Отмена",
		en = "Cancel",
		es = "Cancelar",
		pt = "Cancelar",
	},
	["common.coins"] = {
		ru = "{1} монет",
		en = "{1} coins",
		es = "{1} monedas",
		pt = "{1} moedas",
	},
	["common.robux"] = {
		ru = "{1} Robux",
		en = "{1} Robux",
		es = "{1} Robux",
		pt = "{1} Robux",
	},
	["common.tier"] = {
		ru = "ур. {1}",
		en = "lv. {1}",
		es = "nv. {1}",
		pt = "nv. {1}",
	},
	["common.perSecond"] = {
		ru = "+{1} в сек.",
		en = "+{1}/sec",
		es = "+{1}/s",
		pt = "+{1}/s",
	},
	["common.failed"] = {
		ru = "Не вышло",
		en = "That didn't work",
		es = "No funcionó",
		pt = "Não deu certo",
	},

	-- ---- rarity ----
	["rarity.common"] = {
		ru = "Обычный",
		en = "Common",
		es = "Común",
		pt = "Comum",
	},
	["rarity.rare"] = {
		ru = "Редкий",
		en = "Rare",
		es = "Raro",
		pt = "Raro",
	},
	["rarity.epic"] = {
		ru = "Эпический",
		en = "Epic",
		es = "Épico",
		pt = "Épico",
	},
	["rarity.legendary"] = {
		ru = "Легендарный",
		en = "Legendary",
		es = "Legendario",
		pt = "Lendário",
	},
	["rarity.mythic"] = {
		ru = "Мифический",
		en = "Mythic",
		es = "Mítico",
		pt = "Mítico",
	},

	-- ---- squishes ----
	["squish.dumpling"] = {
		ru = "Пельмешек",
		en = "Dumpling",
		es = "Empanadilla",
		pt = "Pastelzinho",
	},
	["squish.mochi"] = {
		ru = "Моти",
		en = "Mochi",
		es = "Mochi",
		pt = "Mochi",
	},
	["squish.toast"] = {
		ru = "Тостик",
		en = "Toastie",
		es = "Tostadita",
		pt = "Torradinha",
	},
	["squish.boba"] = {
		ru = "Боба",
		en = "Boba",
		es = "Boba",
		pt = "Boba",
	},
	["squish.cloud"] = {
		ru = "Облачко",
		en = "Cloudlet",
		es = "Nubecita",
		pt = "Nuvenzinha",
	},
	["squish.frog"] = {
		ru = "Лягушка-зефирка",
		en = "Marsh Frog",
		es = "Rana Malvavisco",
		pt = "Sapo Marshmallow",
	},
	["squish.pandaBao"] = {
		ru = "Панда-бао",
		en = "Panda Bao",
		es = "Panda Bao",
		pt = "Panda Bao",
	},
	["squish.pudding"] = {
		ru = "Пудинг",
		en = "Pudding",
		es = "Flan",
		pt = "Pudim",
	},
	["squish.rainbowTaiyaki"] = {
		ru = "Радужный тайяки",
		en = "Rainbow Taiyaki",
		es = "Taiyaki Arcoíris",
		pt = "Taiyaki Arco-íris",
	},
	["squish.starMacaron"] = {
		ru = "Звёздный макарон",
		en = "Star Macaron",
		es = "Macarón Estelar",
		pt = "Macaron Estelar",
	},
	["squish.jellyDragon"] = {
		ru = "Желейный дракоша",
		en = "Jelly Dragon",
		es = "Dragoncito de Gelatina",
		pt = "Dragãozinho de Gelatina",
	},
	["squish.pumpkinPie"] = {
		ru = "Тыквенный пирожок",
		en = "Pumpkin Pie",
		es = "Pastel de Calabaza",
		pt = "Torta de Abóbora",
	},
	["squish.snowDango"] = {
		ru = "Снежный данго",
		en = "Snow Dango",
		es = "Dango de Nieve",
		pt = "Dango de Neve",
	},
	["squish.sakuraBun"] = {
		ru = "Сакура-булочка",
		en = "Sakura Bun",
		es = "Bollo Sakura",
		pt = "Pãozinho Sakura",
	},
	["squish.melonJelly"] = {
		ru = "Арбузное желе",
		en = "Melon Jelly",
		es = "Gelatina de Sandía",
		pt = "Gelatina de Melancia",
	},

	-- ---- boxes ----
	["box.caramel"] = {
		ru = "Карамельная коробка",
		en = "Caramel Box",
		es = "Caja de Caramelo",
		pt = "Caixa de Caramelo",
	},
	["box.cloud"] = {
		ru = "Облачная коробка",
		en = "Cloud Box",
		es = "Caja de Nube",
		pt = "Caixa de Nuvem",
	},
	["box.star"] = {
		ru = "Звёздная коробка",
		en = "Star Box",
		es = "Caja Estelar",
		pt = "Caixa Estelar",
	},
	["box.rainbow"] = {
		ru = "Радужная коробка",
		en = "Rainbow Box",
		es = "Caja Arcoíris",
		pt = "Caixa Arco-íris",
	},
	["box.title"] = {
		ru = "Коробки с сюрпризом",
		en = "Surprise boxes",
		es = "Cajas sorpresa",
		pt = "Caixas surpresa",
	},
	["box.open"] = {
		ru = "Открыть",
		en = "Open",
		es = "Abrir",
		pt = "Abrir",
	},
	["box.odds"] = {
		ru = "Шансы",
		en = "Odds",
		es = "Probabilidades",
		pt = "Chances",
	},
	["box.pity"] = {
		ru = "{1} или лучше: не позже чем в {2}-й коробке",
		en = "{1} or better: guaranteed by box {2}",
		es = "{1} o mejor: garantizado en la caja {2}",
		pt = "{1} ou melhor: garantido até a caixa {2}",
	},
	["box.pityLeft"] = {
		ru = "До гарантии: {1}",
		en = "Until guarantee: {1}",
		es = "Hasta la garantía: {1}",
		pt = "Até a garantia: {1}",
	},
	["box.notEnough"] = {
		ru = "Не хватает монет",
		en = "Not enough coins",
		es = "No tienes suficientes monedas",
		pt = "Moedas insuficientes",
	},
	["box.toPocket"] = {
		ru = "Полки заняты, сквиш отправлен в карман",
		en = "Shelves are full, the squish went to your pocket",
		es = "Estantes llenos: el squishy fue a tu bolsillo",
		pt = "Prateleiras cheias: o squishy foi para o bolso",
	},
	["box.full"] = {
		ru = "Слишком много сквишей. Слей или продай лишних",
		en = "Too many squishes. Merge or sell some first",
		es = "Demasiados squishies. Fusiona o vende algunos",
		pt = "Squishies demais. Junte ou venda alguns",
	},
	["box.paidNote"] = {
		ru = "Случайный сквиш за Robux. Шансы показаны выше",
		en = "A random squish for Robux. Odds are shown above",
		es = "Un squishy aleatorio por Robux. Las probabilidades están arriba",
		pt = "Um squishy aleatório por Robux. As chances estão acima",
	},
	["box.machine"] = {
		ru = "Коробки",
		en = "Boxes",
		es = "Cajas",
		pt = "Caixas",
	},
	["box.new"] = {
		ru = "Новый!",
		en = "New!",
		es = "¡Nuevo!",
		pt = "Novo!",
	},

	-- ---- base ----
	["base.sign"] = {
		ru = "База: {1}",
		en = "{1}'s base",
		es = "Base de {1}",
		pt = "Base de {1}",
	},
	["base.title"] = {
		ru = "Моя база",
		en = "My base",
		es = "Mi base",
		pt = "Minha base",
	},
	["base.slots"] = {
		ru = "Полки: {1} из {2}",
		en = "Shelves: {1} of {2}",
		es = "Estantes: {1} de {2}",
		pt = "Prateleiras: {1} de {2}",
	},
	["base.buySlot"] = {
		ru = "Новая полка: {1}",
		en = "New shelf: {1}",
		es = "Nuevo estante: {1}",
		pt = "Nova prateleira: {1}",
	},
	["base.slotsMax"] = {
		ru = "Все полки куплены",
		en = "Every shelf bought",
		es = "Todos los estantes comprados",
		pt = "Todas as prateleiras compradas",
	},
	["base.pocket"] = {
		ru = "Карман",
		en = "Pocket",
		es = "Bolsillo",
		pt = "Bolso",
	},
	["base.pocketEmpty"] = {
		ru = "В кармане пусто",
		en = "Your pocket is empty",
		es = "Tu bolsillo está vacío",
		pt = "Seu bolso está vazio",
	},
	["base.place"] = {
		ru = "На полку",
		en = "To shelf",
		es = "Al estante",
		pt = "Na prateleira",
	},
	["base.store"] = {
		ru = "В карман",
		en = "To pocket",
		es = "Al bolsillo",
		pt = "No bolso",
	},
	["base.sell"] = {
		ru = "Продать: {1}",
		en = "Sell: {1}",
		es = "Vender: {1}",
		pt = "Vender: {1}",
	},
	["base.merge"] = {
		ru = "Слить",
		en = "Merge",
		es = "Fusionar",
		pt = "Juntar",
	},
	["base.mergeDone"] = {
		ru = "{1} вырос до уровня {2}!",
		en = "{1} grew to level {2}!",
		es = "¡{1} subió al nivel {2}!",
		pt = "{1} subiu para o nível {2}!",
	},
	["base.mergeHint"] = {
		ru = "Два одинаковых сквиша одного уровня сливаются в одного большого",
		en = "Two identical squishes of the same level merge into one bigger squish",
		es = "Dos squishies iguales del mismo nivel se fusionan en uno más grande",
		pt = "Dois squishies iguais do mesmo nível viram um maior",
	},
	["base.noMerge"] = {
		ru = "Нет пары для слияния",
		en = "No pair to merge",
		es = "No hay pareja para fusionar",
		pt = "Não há par para juntar",
	},
	["base.shelvesFull"] = {
		ru = "Все полки заняты",
		en = "All shelves are taken",
		es = "Todos los estantes están ocupados",
		pt = "Todas as prateleiras estão ocupadas",
	},
	["base.lastShelf"] = {
		ru = "Хотя бы один сквиш должен остаться на полке",
		en = "Keep at least one squish on a shelf",
		es = "Deja al menos un squishy en un estante",
		pt = "Deixe pelo menos um squishy na prateleira",
	},
	["base.shield"] = {
		ru = "Щит: {1}",
		en = "Shield: {1}",
		es = "Escudo: {1}",
		pt = "Escudo: {1}",
	},
	["base.protected"] = {
		ru = "Новичок: базу не тронут ещё {1}",
		en = "New player: your base is safe for {1}",
		es = "Novato: tu base está a salvo {1}",
		pt = "Novato: sua base está segura por {1}",
	},

	-- ---- steal ----
	["steal.action"] = {
		ru = "Утащить",
		en = "Grab",
		es = "Agarrar",
		pt = "Pegar",
	},
	["steal.carrying"] = {
		ru = "Неси домой!",
		en = "Run home!",
		es = "¡Corre a casa!",
		pt = "Corre pra casa!",
	},
	["steal.slipped"] = {
		ru = "Ой! Сквиш выскользнул",
		en = "Oops! The squish slipped away",
		es = "¡Uy! El squishy se escapó",
		pt = "Ops! O squishy escorregou",
	},
	["steal.delivered"] = {
		ru = "{1} теперь живёт у тебя",
		en = "{1} lives with you now",
		es = "{1} ahora vive contigo",
		pt = "{1} agora mora com você",
	},
	["steal.ranHome"] = {
		ru = "{1} соскучился и убежал домой",
		en = "{1} missed home and ran back",
		es = "{1} extrañó su casa y volvió",
		pt = "{1} sentiu saudade e voltou para casa",
	},
	["steal.robbed"] = {
		ru = "{1} уносит твоего сквиша: {2}. Догоняй с подушкой!",
		en = "{1} is carrying off your {2}. Catch them with your pillow!",
		es = "{1} se lleva tu {2}. ¡Alcánzalo con la almohada!",
		pt = "{1} está levando seu {2}. Alcance com o travesseiro!",
	},
	["steal.lost"] = {
		ru = "{1} забрал твоего сквиша: {2}",
		en = "{1} took your {2}",
		es = "{1} se llevó tu {2}",
		pt = "{1} levou seu {2}",
	},
	["steal.returned"] = {
		ru = "{1} вернулся домой",
		en = "{1} is back home",
		es = "{1} volvió a casa",
		pt = "{1} voltou para casa",
	},
	["steal.knocked"] = {
		ru = "Бум подушкой! Сквиш вылетел",
		en = "Pillow bonk! The squish flew loose",
		es = "¡Almohadazo! El squishy salió volando",
		pt = "Travesseirada! O squishy voou longe",
	},
	["steal.reason.newbie"] = {
		ru = "Новичка пока не трогаем",
		en = "New players are protected for now",
		es = "Los novatos están protegidos por ahora",
		pt = "Novatos estão protegidos por enquanto",
	},
	["steal.reason.shield"] = {
		ru = "Эта база под щитом",
		en = "This base is shielded",
		es = "Esta base tiene escudo",
		pt = "Esta base está com escudo",
	},
	["steal.reason.dailyCap"] = {
		ru = "Эту базу сегодня хватит обижать",
		en = "This base has lost enough for today",
		es = "Esta base ya perdió bastante hoy",
		pt = "Esta base já perdeu o bastante hoje",
	},
	["steal.reason.lastSquish"] = {
		ru = "Последнего сквиша не берём",
		en = "We never take someone's last squish",
		es = "Nunca nos llevamos el último squishy",
		pt = "Nunca pegamos o último squishy",
	},
	["steal.reason.offline"] = {
		ru = "Хозяина нет в игре",
		en = "The owner isn't here",
		es = "El dueño no está",
		pt = "O dono não está aqui",
	},
	["steal.reason.noRoom"] = {
		ru = "Освободи полку дома, чтобы было куда нести",
		en = "Free a shelf at home first",
		es = "Libera un estante en casa primero",
		pt = "Libere uma prateleira em casa primeiro",
	},
	["steal.reason.busy"] = {
		ru = "Руки уже заняты",
		en = "Your hands are full",
		es = "Tienes las manos ocupadas",
		pt = "Suas mãos estão ocupadas",
	},
	["pillow.name"] = {
		ru = "Подушка",
		en = "Pillow",
		es = "Almohada",
		pt = "Travesseiro",
	},

	-- ---- traps ----
	["trap.trampoline"] = {
		ru = "Батут",
		en = "Trampoline",
		es = "Trampolín",
		pt = "Cama elástica",
	},
	["trap.slime"] = {
		ru = "Лужа слайма",
		en = "Slime puddle",
		es = "Charco de slime",
		pt = "Poça de slime",
	},
	["trap.cannon"] = {
		ru = "Подушечная пушка",
		en = "Pillow cannon",
		es = "Cañón de almohadas",
		pt = "Canhão de travesseiros",
	},
	["trap.trampoline.desc"] = {
		ru = "Подбрасывает вора обратно в базу",
		en = "Bounces a thief back into your base",
		es = "Rebota al ladrón de vuelta a tu base",
		pt = "Joga o ladrão de volta para a base",
	},
	["trap.slime.desc"] = {
		ru = "Вор вязнет и идёт медленнее",
		en = "Thieves get stuck and slow down",
		es = "Los ladrones se atascan y van más lento",
		pt = "Ladrões grudam e ficam lentos",
	},
	["trap.cannon.desc"] = {
		ru = "Стреляет подушками, выбивает сквиша из рук",
		en = "Fires pillows that knock squishes loose",
		es = "Dispara almohadas que sueltan al squishy",
		pt = "Atira travesseiros que soltam o squishy",
	},
	["trap.title"] = {
		ru = "Ловушки у входа",
		en = "Entrance traps",
		es = "Trampas de la entrada",
		pt = "Armadilhas da entrada",
	},
	["trap.level"] = {
		ru = "Уровень {1}",
		en = "Level {1}",
		es = "Nivel {1}",
		pt = "Nível {1}",
	},
	["trap.build"] = {
		ru = "Поставить: {1}",
		en = "Build: {1}",
		es = "Construir: {1}",
		pt = "Construir: {1}",
	},
	["trap.upgrade"] = {
		ru = "Улучшить: {1}",
		en = "Upgrade: {1}",
		es = "Mejorar: {1}",
		pt = "Melhorar: {1}",
	},
	["trap.max"] = {
		ru = "Максимум",
		en = "Maxed",
		es = "Al máximo",
		pt = "No máximo",
	},
	["trap.note"] = {
		ru = "Ловушки трогают только того, кто несёт твоего сквиша",
		en = "Traps only touch someone carrying your squish",
		es = "Las trampas solo afectan a quien lleva tu squishy",
		pt = "Armadilhas só pegam quem leva seu squishy",
	},

	-- ---- hud ----
	["hud.shop"] = {
		ru = "Магазин",
		en = "Shop",
		es = "Tienda",
		pt = "Loja",
	},
	["hud.trade"] = {
		ru = "Обмен",
		en = "Trade",
		es = "Intercambio",
		pt = "Troca",
	},
	["hud.show"] = {
		ru = "Шоу",
		en = "Show",
		es = "Show",
		pt = "Show",
	},
	["hud.base"] = {
		ru = "База",
		en = "Base",
		es = "Base",
		pt = "Base",
	},
	["hud.boost"] = {
		ru = "x{1} на {2}",
		en = "x{1} for {2}",
		es = "x{1} por {2}",
		pt = "x{1} por {2}",
	},

	-- ---- shop ----
	["shop.title"] = {
		ru = "Магазин",
		en = "Shop",
		es = "Tienda",
		pt = "Loja",
	},
	["shop.passes"] = {
		ru = "Навсегда",
		en = "Forever",
		es = "Para siempre",
		pt = "Para sempre",
	},
	["shop.products"] = {
		ru = "Разовое",
		en = "One-time",
		es = "De una vez",
		pt = "Avulso",
	},
	["shop.ads"] = {
		ru = "За рекламу",
		en = "Watch an ad",
		es = "Por anuncio",
		pt = "Por anúncio",
	},
	["shop.owned"] = {
		ru = "Уже твоё",
		en = "Owned",
		es = "Ya es tuyo",
		pt = "Já é seu",
	},
	["shop.soon"] = {
		ru = "Скоро",
		en = "Soon",
		es = "Pronto",
		pt = "Em breve",
	},
	["pass.doubleCoins"] = {
		ru = "Двойные монеты",
		en = "Double coins",
		es = "Monedas dobles",
		pt = "Moedas em dobro",
	},
	["pass.doubleCoins.desc"] = {
		ru = "Все сквиши приносят в два раза больше",
		en = "Every squish earns twice as much",
		es = "Cada squishy gana el doble",
		pt = "Cada squishy rende o dobro",
	},
	["pass.bigShelf"] = {
		ru = "Большой стеллаж",
		en = "Big shelving",
		es = "Estantería grande",
		pt = "Estante grande",
	},
	["pass.bigShelf.desc"] = {
		ru = "+4 полки в базе",
		en = "+4 shelves at your base",
		es = "+4 estantes en tu base",
		pt = "+4 prateleiras na base",
	},
	["pass.comfyGloves"] = {
		ru = "Мягкие перчатки",
		en = "Comfy gloves",
		es = "Guantes suaves",
		pt = "Luvas macias",
	},
	["pass.comfyGloves.desc"] = {
		ru = "Сжатие приносит в два раза больше",
		en = "Squeezing pays double",
		es = "Apretar paga el doble",
		pt = "Apertar rende o dobro",
	},
	["product.rainbowBox"] = {
		ru = "Радужная коробка",
		en = "Rainbow Box",
		es = "Caja Arcoíris",
		pt = "Caixa Arco-íris",
	},
	["product.rainbowBox.desc"] = {
		ru = "Редкий или лучше. Шансы перед покупкой",
		en = "Rare or better. Odds shown before you buy",
		es = "Raro o mejor. Probabilidades antes de comprar",
		pt = "Raro ou melhor. Chances antes de comprar",
	},
	["product.sugarRush"] = {
		ru = "Сахарный разгон",
		en = "Sugar rush",
		es = "Subidón de azúcar",
		pt = "Pico de açúcar",
	},
	["product.sugarRush.desc"] = {
		ru = "x3 монет на 15 минут",
		en = "x3 coins for 15 minutes",
		es = "x3 monedas por 15 minutos",
		pt = "x3 moedas por 15 minutos",
	},
	["product.pillowFort"] = {
		ru = "Крепость из подушек",
		en = "Pillow fort",
		es = "Fuerte de almohadas",
		pt = "Forte de travesseiros",
	},
	["product.pillowFort.desc"] = {
		ru = "Щит на базу на 1 час",
		en = "Shield your base for 1 hour",
		es = "Escudo para tu base por 1 hora",
		pt = "Escudo na base por 1 hora",
	},
	["ad.adIncomeBoost"] = {
		ru = "x2 монет на 15 минут",
		en = "x2 coins for 15 minutes",
		es = "x2 monedas por 15 minutos",
		pt = "x2 moedas por 15 minutos",
	},
	["ad.adShield"] = {
		ru = "Щит на 10 минут",
		en = "Shield for 10 minutes",
		es = "Escudo por 10 minutos",
		pt = "Escudo por 10 minutos",
	},
	["ad.adCoinGift"] = {
		ru = "Монеты за 3 минуты сразу",
		en = "3 minutes of coins now",
		es = "3 minutos de monedas ya",
		pt = "3 minutos de moedas agora",
	},
	["ad.watch"] = {
		ru = "Смотреть",
		en = "Watch",
		es = "Ver",
		pt = "Assistir",
	},
	["ad.cooldown"] = {
		ru = "Через {1}",
		en = "In {1}",
		es = "En {1}",
		pt = "Em {1}",
	},
	["ad.limit"] = {
		ru = "На сегодня всё",
		en = "Done for today",
		es = "Listo por hoy",
		pt = "Acabou por hoje",
	},

	-- ---- show ----
	["show.title"] = {
		ru = "Сквиш-шоу",
		en = "Squish Show",
		es = "Squish Show",
		pt = "Squish Show",
	},
	["show.score"] = {
		ru = "Твои очки: {1}",
		en = "Your score: {1}",
		es = "Tu puntuación: {1}",
		pt = "Sua pontuação: {1}",
	},
	["show.how"] = {
		ru = "Считаются {1} лучших сквишей коллекции",
		en = "Your best {1} squishes count",
		es = "Cuentan tus {1} mejores squishies",
		pt = "Contam seus {1} melhores squishies",
	},
	["show.ends"] = {
		ru = "До итогов: {1}",
		en = "Results in: {1}",
		es = "Resultados en: {1}",
		pt = "Resultado em: {1}",
	},
	["show.prize"] = {
		ru = "Лучшие {1} получат значок и сезонного сквиша: {2}",
		en = "The top {1} win a badge and a seasonal squish: {2}",
		es = "Los {1} mejores ganan una insignia y un squishy de temporada: {2}",
		pt = "Os {1} melhores ganham um emblema e um squishy da estação: {2}",
	},
	["show.won"] = {
		ru = "Ты в десятке лучших! Подарок: {1}",
		en = "You made the top ten! Your prize: {1}",
		es = "¡Estás en el top diez! Tu premio: {1}",
		pt = "Você está no top dez! Seu prêmio: {1}",
	},
	["show.top"] = {
		ru = "Лучшие на этой неделе",
		en = "This week's best",
		es = "Los mejores de la semana",
		pt = "Os melhores da semana",
	},
	["show.empty"] = {
		ru = "Пока никто не участвует",
		en = "No entries yet",
		es = "Aún no hay participantes",
		pt = "Ainda não há participantes",
	},

	-- ---- trade ----
	["trade.title"] = {
		ru = "Обмен",
		en = "Trade",
		es = "Intercambio",
		pt = "Troca",
	},
	["trade.pick"] = {
		ru = "С кем меняемся?",
		en = "Trade with whom?",
		es = "¿Con quién intercambias?",
		pt = "Trocar com quem?",
	},
	["trade.request"] = {
		ru = "{1} предлагает обмен",
		en = "{1} wants to trade",
		es = "{1} quiere intercambiar",
		pt = "{1} quer trocar",
	},
	["trade.accept"] = {
		ru = "Давай",
		en = "Sure",
		es = "Vale",
		pt = "Bora",
	},
	["trade.decline"] = {
		ru = "Не сейчас",
		en = "Not now",
		es = "Ahora no",
		pt = "Agora não",
	},
	["trade.yours"] = {
		ru = "Ты отдаёшь",
		en = "You give",
		es = "Tú das",
		pt = "Você dá",
	},
	["trade.theirs"] = {
		ru = "Ты получаешь",
		en = "You get",
		es = "Tú recibes",
		pt = "Você recebe",
	},
	["trade.confirm"] = {
		ru = "Подтвердить",
		en = "Confirm",
		es = "Confirmar",
		pt = "Confirmar",
	},
	["trade.waiting"] = {
		ru = "Ждём второго",
		en = "Waiting for the other player",
		es = "Esperando al otro",
		pt = "Esperando o outro",
	},
	["trade.countdown"] = {
		ru = "Обмен через {1}...",
		en = "Trading in {1}...",
		es = "Intercambio en {1}...",
		pt = "Trocando em {1}...",
	},
	["trade.done"] = {
		ru = "Обмен прошёл!",
		en = "Trade done!",
		es = "¡Intercambio hecho!",
		pt = "Troca feita!",
	},
	["trade.cancelled"] = {
		ru = "Обмен отменён",
		en = "Trade cancelled",
		es = "Intercambio cancelado",
		pt = "Troca cancelada",
	},
	["trade.nobody"] = {
		ru = "Рядом никого нет",
		en = "Nobody to trade with",
		es = "No hay nadie para intercambiar",
		pt = "Ninguém para trocar",
	},
	["trade.reason.tooNew"] = {
		ru = "Обмен откроется после 30 минут игры",
		en = "Trading opens after 30 minutes of play",
		es = "El intercambio se abre tras 30 minutos de juego",
		pt = "A troca abre após 30 minutos de jogo",
	},
	["trade.reason.cooldown"] = {
		ru = "Чуть подожди перед следующим обменом",
		en = "Wait a moment before the next trade",
		es = "Espera un momento antes del siguiente",
		pt = "Espere um pouco antes da próxima troca",
	},
	["trade.reason.fresh"] = {
		ru = "Этот сквиш только что сменил хозяина, подожди 10 минут",
		en = "This squish just changed hands, wait 10 minutes",
		es = "Este squishy acaba de cambiar de dueño, espera 10 minutos",
		pt = "Este squishy acabou de mudar de dono, espere 10 minutos",
	},
	["trade.reason.tooMany"] = {
		ru = "Не больше 4 сквишей с каждой стороны",
		en = "No more than 4 squishes per side",
		es = "No más de 4 squishies por lado",
		pt = "No máximo 4 squishies por lado",
	},
	["trade.reason.full"] = {
		ru = "У кого-то не хватит места",
		en = "Someone has no room for it",
		es = "Alguien no tiene espacio",
		pt = "Alguém não tem espaço",
	},
	["trade.reason.busy"] = {
		ru = "Игрок уже занят обменом",
		en = "That player is already trading",
		es = "Ese jugador ya está intercambiando",
		pt = "Esse jogador já está trocando",
	},
	["trade.reason.notOwned"] = {
		ru = "Этого сквиша уже нет",
		en = "That squish is gone",
		es = "Ese squishy ya no está",
		pt = "Esse squishy não está mais aqui",
	},
	["trade.reason.duplicate"] = {
		ru = "Сквиш уже в предложении",
		en = "That squish is already offered",
		es = "Ese squishy ya está ofrecido",
		pt = "Esse squishy já foi oferecido",
	},
	["trade.reason.lastSquish"] = {
		ru = "Хотя бы один сквиш должен остаться на полке",
		en = "Keep at least one squish on a shelf",
		es = "Deja al menos un squishy en un estante",
		pt = "Deixe pelo menos um squishy na prateleira",
	},
} :: { [string]: Bundle }

--- Looks a key up for a locale and fills its placeholders.
---
--- An unknown key comes back as itself and an unknown locale falls back to
--- English: a visible key on screen is a bug report, a blank space is a mystery.
function Strings.get(key: string, locale: string, ...: any): string
	local bundle = Strings.Entries[key]
	if bundle == nil then
		return key
	end

	local text = (bundle :: any)[locale]
	if typeof(text) ~= "string" then
		text = (bundle :: any)[Strings.Fallback]
	end
	if typeof(text) ~= "string" then
		return key
	end

	local count = select("#", ...)
	if count == 0 then
		return text
	end

	local values = table.pack(...)
	local result = string.gsub(text, "{(%d+)}", function(index: string): string
		local position = tonumber(index)
		if position == nil or position > count then
			-- An unfilled placeholder stays visible, so a missing argument is
			-- seen rather than silently dropped.
			return "{" .. index .. "}"
		end
		return tostring(values[position])
	end)
	return result
end

return Strings
