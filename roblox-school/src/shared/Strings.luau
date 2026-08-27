--!strict
--- Every string a player reads, in every launch locale.
---
--- A plain table rather than a LocalizationTable. Roblox's own localisation is
--- built for static GUI text with AutoLocalize doing the work; almost everything
--- here is assembled at runtime from numbers and names, so it would go through
--- the scripting API regardless. A table has the advantage of being testable
--- outside Roblox: tests/strings.spec.luau asserts that every key exists in all
--- four locales and that the placeholders match across them, which is how a
--- half-finished translation gets caught here instead of in front of a player.
---
--- Placeholders are `{1}`, `{2}` and are positional, because word order differs
--- between these languages and a translator has to be free to move them.

local Strings = {}

export type Bundle = { ru: string, en: string, es: string, pt: string }

Strings.Fallback = "en"

Strings.Entries = {
	-- ---- shared ----
	["common.next"] = { ru = "Дальше", en = "Next", es = "Siguiente", pt = "Próximo" },
	["common.open"] = { ru = "Открыть", en = "Open", es = "Abrir", pt = "Abrir" },
	["common.choose"] = { ru = "Выбрать", en = "Choose", es = "Elegir", pt = "Escolher" },
	["common.save"] = { ru = "Сохранить", en = "Save", es = "Guardar", pt = "Salvar" },
	["common.send"] = { ru = "Отправить", en = "Submit", es = "Enviar", pt = "Enviar" },
	["common.check"] = { ru = "Проверить", en = "Check", es = "Comprobar", pt = "Verificar" },
	["common.leave"] = { ru = "Выйти", en = "Leave", es = "Salir", pt = "Sair" },
	["common.stop"] = { ru = "Стоп", en = "Stop", es = "Parar", pt = "Parar" },
	["common.notNow"] = { ru = "Не сейчас", en = "Not now", es = "Ahora no", pt = "Agora não" },
	["common.failed"] = { ru = "Не вышло", en = "That didn't work", es = "No funcionó", pt = "Não deu certo" },
	["common.grade"] = { ru = "{1} класс", en = "grade {1}", es = "grado {1}", pt = "série {1}" },
	["common.points"] = { ru = "{1} баллов", en = "{1} points", es = "{1} puntos", pt = "{1} pontos" },

	-- ---- lesson ----
	["lesson.progress"] = {
		ru = "Вопрос {1} из {2}",
		en = "Question {1} of {2}",
		es = "Pregunta {1} de {2}",
		pt = "Questão {1} de {2}",
	},
	["lesson.passed"] = { ru = "Урок сдан", en = "Lesson passed", es = "Lección aprobada", pt = "Aula aprovada" },
	["lesson.failed"] = { ru = "Урок не сдан", en = "Lesson not passed", es = "Lección no aprobada", pt = "Aula não aprovada" },
	["lesson.score"] = {
		ru = "Верных ответов: {1} из {2}\n+{3} баллов",
		en = "Correct: {1} of {2}\n+{3} points",
		es = "Correctas: {1} de {2}\n+{3} puntos",
		pt = "Corretas: {1} de {2}\n+{3} pontos",
	},
	["lesson.advanced"] = {
		ru = "Ты перешёл в {1} класс",
		en = "You've moved up to grade {1}",
		es = "Has pasado al grado {1}",
		pt = "Você passou para a série {1}",
	},
	["lesson.graduated"] = {
		ru = "Все классы пройдены. Открой «Школа» и выбери, что дальше.",
		en = "Every grade is behind you. Open School and choose what comes next.",
		es = "Has terminado todos los grados. Abre Escuela y elige qué sigue.",
		pt = "Todas as séries concluídas. Abra Escola e escolha o que vem a seguir.",
	},

	-- ---- obstacle course ----
	["course.checkpoints"] = {
		ru = "Чекпоинты: {1} из {2}",
		en = "Checkpoints: {1} of {2}",
		es = "Puntos de control: {1} de {2}",
		pt = "Pontos de controle: {1} de {2}",
	},
	["course.passed"] = { ru = "Полоса пройдена", en = "Course cleared", es = "Circuito superado", pt = "Percurso concluído" },
	["course.failed"] = { ru = "Полоса не пройдена", en = "Course failed", es = "Circuito fallido", pt = "Percurso não concluído" },
	["course.fell"] = {
		ru = "Сорвался. Обратно на чекпоинт.",
		en = "You fell. Back to the checkpoint.",
		es = "Te caíste. Vuelta al punto de control.",
		pt = "Você caiu. De volta ao ponto de controle.",
	},
	["course.hazard"] = { ru = "Задел препятствие.", en = "You hit an obstacle.", es = "Chocaste con un obstáculo.", pt = "Você bateu num obstáculo." },
	["course.timeLimit"] = { ru = "Время вышло.", en = "Out of time.", es = "Se acabó el tiempo.", pt = "Acabou o tempo." },
	["course.rejected"] = { ru = "Прохождение не засчитано.", en = "That run wasn't counted.", es = "Ese intento no cuenta.", pt = "Essa tentativa não contou." },
	["course.title"] = { ru = "Полоса препятствий", en = "Obstacle course", es = "Circuito de obstáculos", pt = "Percurso de obstáculos" },
	["course.difficulty"] = { ru = "Сложность (класс):", en = "Difficulty (grade):", es = "Dificultad (grado):", pt = "Dificuldade (série):" },
	["course.empty"] = {
		ru = "Пока пусто. Нажимай модули выше.",
		en = "Nothing yet. Tap the modules above.",
		es = "Vacío por ahora. Toca los módulos de arriba.",
		pt = "Vazio por enquanto. Toque nos módulos acima.",
	},
	["course.undo"] = { ru = "Убрать последний", en = "Remove last", es = "Quitar el último", pt = "Remover o último" },
	["course.namePlaceholder"] = { ru = "название полосы", en = "course name", es = "nombre del circuito", pt = "nome do percurso" },
	["course.requirements"] = {
		ru = "Модулей: {1} из {2} · Разных типов: {3} из {4} · Пропасть {5} · Балка {6} · {7}",
		en = "Modules: {1} of {2} · Distinct types: {3} of {4} · Gap {5} · Beam {6} · {7}",
		es = "Módulos: {1} de {2} · Tipos distintos: {3} de {4} · Hueco {5} · Viga {6} · {7}",
		pt = "Módulos: {1} de {2} · Tipos distintos: {3} de {4} · Vão {5} · Viga {6} · {7}",
	},
	["course.noCheckpoints"] = { ru = "без чекпоинтов", en = "no checkpoints", es = "sin puntos de control", pt = "sem pontos de controle" },
	["course.checkpointEvery"] = {
		ru = "чекпоинт каждые {1}",
		en = "checkpoint every {1}",
		es = "punto de control cada {1}",
		pt = "ponto de controle a cada {1}",
	},
	["course.saved"] = { ru = "Полоса сохранена", en = "Course saved", es = "Circuito guardado", pt = "Percurso salvo" },

	-- ---- obstacle modules ----
	["module.gap"] = { ru = "Пропасть", en = "Gap", es = "Hueco", pt = "Vão" },
	["module.narrowBeam"] = { ru = "Узкая балка", en = "Narrow beam", es = "Viga estrecha", pt = "Viga estreita" },
	["module.movingPlatform"] = { ru = "Движущаяся платформа", en = "Moving platform", es = "Plataforma móvil", pt = "Plataforma móvel" },
	["module.vanishingTiles"] = { ru = "Исчезающие плитки", en = "Vanishing tiles", es = "Baldosas que desaparecen", pt = "Ladrilhos que somem" },
	["module.spinner"] = { ru = "Вертушка", en = "Spinner", es = "Girador", pt = "Girador" },
	["module.hazardField"] = { ru = "Поле шипов", en = "Spike field", es = "Campo de púas", pt = "Campo de espinhos" },

	-- ---- assembly ----
	["assembly.palette"] = {
		ru = "Детали — лишние тоже есть",
		en = "Parts — some of these don't belong",
		es = "Piezas — algunas sobran",
		pt = "Peças — algumas sobram",
	},
	["assembly.passed"] = { ru = "Задание зачтено", en = "Task complete", es = "Tarea completada", pt = "Tarefa concluída" },
	["assembly.failed"] = { ru = "Задание не зачтено", en = "Task not complete", es = "Tarea incompleta", pt = "Tarefa incompleta" },
	["assembly.result"] = {
		ru = "{1} · верно {2} из {3} · +{4} баллов\nПравильно: {5}\n{6}",
		en = "{1} · {2} of {3} right · +{4} points\nCorrect: {5}\n{6}",
		es = "{1} · {2} de {3} correctas · +{4} puntos\nCorrecto: {5}\n{6}",
		pt = "{1} · {2} de {3} certas · +{4} pontos\nCorreto: {5}\n{6}",
	},

	-- ---- assembly components ----
	["component.battery"] = { ru = "Батарейка", en = "Battery", es = "Pila", pt = "Pilha" },
	["component.wire"] = { ru = "Провод", en = "Wire", es = "Cable", pt = "Fio" },
	["component.lamp"] = { ru = "Лампа", en = "Lamp", es = "Bombilla", pt = "Lâmpada" },
	["component.switch"] = { ru = "Выключатель", en = "Switch", es = "Interruptor", pt = "Interruptor" },
	["component.resistor"] = { ru = "Резистор", en = "Resistor", es = "Resistencia", pt = "Resistor" },
	["component.magnet"] = { ru = "Магнит", en = "Magnet", es = "Imán", pt = "Ímã" },
	["component.thermometer"] = { ru = "Термометр", en = "Thermometer", es = "Termómetro", pt = "Termômetro" },
	["component.beaker"] = { ru = "Стакан", en = "Beaker", es = "Vaso", pt = "Copo" },
	["component.funnel"] = { ru = "Воронка", en = "Funnel", es = "Embudo", pt = "Funil" },
	["component.filter"] = { ru = "Фильтр", en = "Filter", es = "Filtro", pt = "Filtro" },
	["component.seed"] = { ru = "Семечко", en = "Seed", es = "Semilla", pt = "Semente" },
	["component.soil"] = { ru = "Земля", en = "Soil", es = "Tierra", pt = "Terra" },
	["component.water"] = { ru = "Вода", en = "Water", es = "Agua", pt = "Água" },
	["component.sunlight"] = { ru = "Свет", en = "Sunlight", es = "Luz del sol", pt = "Luz do sol" },
	["component.sprout"] = { ru = "Росток", en = "Sprout", es = "Brote", pt = "Broto" },
	["component.red"] = { ru = "Красный", en = "Red", es = "Rojo", pt = "Vermelho" },
	["component.blue"] = { ru = "Синий", en = "Blue", es = "Azul", pt = "Azul" },
	["component.yellow"] = { ru = "Жёлтый", en = "Yellow", es = "Amarillo", pt = "Amarelo" },
	["component.green"] = { ru = "Зелёный", en = "Green", es = "Verde", pt = "Verde" },
	["component.orange"] = { ru = "Оранжевый", en = "Orange", es = "Naranja", pt = "Laranja" },
	["component.purple"] = { ru = "Фиолетовый", en = "Purple", es = "Morado", pt = "Roxo" },
	["component.sky"] = { ru = "Небо", en = "Sky", es = "Cielo", pt = "Céu" },
	["component.horizon"] = { ru = "Горизонт", en = "Horizon", es = "Horizonte", pt = "Horizonte" },
	["component.foreground"] = { ru = "Передний план", en = "Foreground", es = "Primer plano", pt = "Primeiro plano" },
	["component.shadow"] = { ru = "Тень", en = "Shadow", es = "Sombra", pt = "Sombra" },
	["component.highlight"] = { ru = "Блик", en = "Highlight", es = "Brillo", pt = "Brilho" },

	-- ---- subjects ----
	["subject.math"] = { ru = "Математика", en = "Maths", es = "Matemáticas", pt = "Matemática" },
	["subject.science"] = { ru = "Наука", en = "Science", es = "Ciencias", pt = "Ciências" },
	["subject.logic"] = { ru = "Логика", en = "Logic", es = "Lógica", pt = "Lógica" },
	["subject.pe"] = { ru = "Физкультура", en = "PE", es = "Educación física", pt = "Educação física" },
	["subject.art"] = { ru = "Искусство", en = "Art", es = "Arte", pt = "Arte" },
	["subject.literature"] = { ru = "Литература", en = "Literature", es = "Literatura", pt = "Literatura" },
	["subject.history"] = { ru = "История", en = "History", es = "Historia", pt = "História" },
	["subject.language"] = { ru = "Родной язык", en = "Language", es = "Lengua", pt = "Língua" },

	-- ---- classes ----
	["class.title"] = { ru = "Школа", en = "School", es = "Escuela", pt = "Escola" },
	["class.browse"] = { ru = "Классы", en = "Classes", es = "Clases", pt = "Turmas" },
	["class.mine"] = { ru = "Мой класс", en = "My class", es = "Mi clase", pt = "Minha turma" },
	["class.join"] = { ru = "Вступить", en = "Join", es = "Unirse", pt = "Entrar" },
	["class.create"] = { ru = "Создать класс", en = "Create a class", es = "Crear una clase", pt = "Criar uma turma" },
	["class.empty"] = {
		ru = "Пока нет классов. Создай свой или учись у ботов.",
		en = "No classes yet. Start one, or learn from the bots.",
		es = "Aún no hay clases. Crea una o aprende con los bots.",
		pt = "Ainda não há turmas. Crie uma ou aprenda com os bots.",
	},
	["class.noRatings"] = { ru = "нет оценок", en = "unrated", es = "sin valoraciones", pt = "sem avaliações" },
	["class.rateThis"] = { ru = "Оценить класс:", en = "Rate this class:", es = "Valorar esta clase:", pt = "Avaliar esta turma:" },
	["class.rated"] = { ru = "Оценка учтена", en = "Rating recorded", es = "Valoración registrada", pt = "Avaliação registrada" },
	["class.start"] = { ru = "Начать", en = "Start", es = "Empezar", pt = "Começar" },
	["class.promote"] = { ru = "Продвинуть", en = "Promote", es = "Promocionar", pt = "Promover" },
	["class.teachLive"] = { ru = "Вести живьём", en = "Teach live", es = "Dar en vivo", pt = "Dar ao vivo" },
	["class.course"] = { ru = "Полоса", en = "Course", es = "Circuito", pt = "Percurso" },
	["class.earned"] = {
		ru = "Накоплено за преподавание: {1}",
		en = "Earned from teaching: {1}",
		es = "Ganado enseñando: {1}",
		pt = "Ganho ensinando: {1}",
	},
	["class.collect"] = { ru = "Забрать", en = "Collect", es = "Cobrar", pt = "Receber" },
	["class.collected"] = {
		ru = "Забрано баллов: {1}",
		en = "Collected {1} points",
		es = "Cobrados {1} puntos",
		pt = "Recebidos {1} pontos",
	},
	["class.myQuestions"] = { ru = "Свои вопросы", en = "My questions", es = "Mis preguntas", pt = "Minhas questões" },
	["class.none"] = {
		ru = "Класса ещё нет. Заполни поля ниже и создай.",
		en = "No class yet. Fill in the fields below to start one.",
		es = "Aún no tienes clase. Rellena los campos de abajo.",
		pt = "Ainda sem turma. Preencha os campos abaixo.",
	},
	["class.lessonCount"] = { ru = "уроков: {1}", en = "{1} lessons", es = "{1} lecciones", pt = "{1} aulas" },
	["class.gradePlaceholder"] = { ru = "класс", en = "grade", es = "grado", pt = "série" },
	["class.subjectPlaceholder"] = { ru = "предмет", en = "subject", es = "materia", pt = "matéria" },
	["class.namePlaceholder"] = { ru = "название класса", en = "class name", es = "nombre de la clase", pt = "nome da turma" },

	-- ---- graduation ----
	["graduation.prompt"] = {
		ru = "Все классы пройдены. Что дальше?",
		en = "Every grade is behind you. What now?",
		es = "Has terminado todos los grados. ¿Y ahora?",
		pt = "Todas as séries concluídas. E agora?",
	},
	["graduation.university"] = { ru = "Поступить в университет", en = "Go to university", es = "Ir a la universidad", pt = "Ir para a universidade" },
	["graduation.teacher"] = { ru = "Стать преподавателем", en = "Become a teacher", es = "Hacerse profesor", pt = "Tornar-se professor" },
	["graduation.newGamePlus"] = { ru = "Пойти заново с бонусом", en = "Start over with a bonus", es = "Empezar de nuevo con bono", pt = "Recomeçar com bônus" },
	["graduation.nowTeacher"] = {
		ru = "Теперь ты преподаватель. Создай свой класс.",
		en = "You're a teacher now. Start your class.",
		es = "Ahora eres profesor. Crea tu clase.",
		pt = "Agora você é professor. Crie sua turma.",
	},
	["graduation.congratulations"] = { ru = "Поздравляю с выпуском!", en = "Congratulations on graduating!", es = "¡Felicidades por graduarte!", pt = "Parabéns pela formatura!" },

	-- ---- campus ----
	["world.library"] = { ru = "Библиотека", en = "Library", es = "Biblioteca", pt = "Biblioteca" },
	["world.staffroom"] = { ru = "Учительская", en = "Staff room", es = "Sala de profesores", pt = "Sala dos professores" },
	["world.gym"] = { ru = "Спортзал", en = "Gym", es = "Gimnasio", pt = "Ginásio" },
	["world.assembly"] = { ru = "Актовый зал", en = "Assembly hall", es = "Salón de actos", pt = "Auditório" },
	["ad.doubleStreak"] = { ru = "Удвоить дневной бонус", en = "Double today's daily bonus", es = "Duplicar el bono diario", pt = "Dobrar o bônus diário" },
	["achv.streakReward"] = { ru = "Дневной бонус: +{1}", en = "Daily bonus: +{1}", es = "Bono diario: +{1}", pt = "Bônus diário: +{1}" },
	["hud.pending"] = { ru = "к получению: {1}", en = "{1} to collect", es = "{1} por cobrar", pt = "{1} a receber" },
	["hud.boosts"] = { ru = "бустов: {1}", en = "{1} boosts", es = "{1} mejoras", pt = "{1} impulsos" },
	["achv.title"] = { ru = "Достижения", en = "Achievements", es = "Logros", pt = "Conquistas" },
	["achv.scholar"] = { ru = "Учёный", en = "Scholar", es = "Erudito", pt = "Erudito" },
	["achv.perfectionist"] = { ru = "Перфекционист", en = "Perfectionist", es = "Perfeccionista", pt = "Perfeccionista" },
	["achv.athlete"] = { ru = "Атлет", en = "Athlete", es = "Atleta", pt = "Atleta" },
	["achv.polymath"] = { ru = "Эрудит", en = "Polymath", es = "Polímata", pt = "Polímata" },
	["achv.regular"] = { ru = "Завсегдатай", en = "Regular", es = "Habitual", pt = "Frequentador" },
	["achv.graduate"] = { ru = "Выпускник", en = "Graduate", es = "Graduado", pt = "Formado" },
	["achv.mentor"] = { ru = "Наставник", en = "Mentor", es = "Mentor", pt = "Mentor" },
	["achv.faculty"] = { ru = "Методист", en = "Faculty", es = "Docente", pt = "Docente" },
	["achv.acclaimed"] = { ru = "Признанный", en = "Acclaimed", es = "Aclamado", pt = "Aclamado" },
	["achv.citizen"] = { ru = "Гражданин", en = "Citizen", es = "Ciudadano", pt = "Cidadão" },
	["achv.progress"] = { ru = "{1} / {2}", en = "{1} / {2}", es = "{1} / {2}", pt = "{1} / {2}" },
	["achv.unlocked"] = { ru = "Открыто: {1}", en = "Unlocked: {1}", es = "Desbloqueado: {1}", pt = "Desbloqueado: {1}" },
	["achv.reward"] = { ru = "+{1} баллов", en = "+{1} points", es = "+{1} puntos", pt = "+{1} pontos" },
	["achv.done"] = { ru = "Ветка пройдена", en = "Branch complete", es = "Rama completa", pt = "Ramo completo" },
	["achv.perks"] = { ru = "Постоянные бонусы", en = "Permanent perks", es = "Ventajas permanentes", pt = "Vantagens permanentes" },
	["achv.streak"] = { ru = "Серия: {1} дн.", en = "Streak: {1} days", es = "Racha: {1} días", pt = "Sequência: {1} dias" },
	["achv.streakToday"] = { ru = "День {1} подряд", en = "Day {1} in a row", es = "Día {1} seguido", pt = "Dia {1} seguido" },
	["perk.studentPoints"] = { ru = "Очки за урок ×{1}", en = "Lesson points ×{1}", es = "Puntos por lección ×{1}", pt = "Pontos por aula ×{1}" },
	["perk.teacherPayout"] = { ru = "Доход преподавателя ×{1}", en = "Teaching income ×{1}", es = "Ingresos docentes ×{1}", pt = "Renda docente ×{1}" },
	["perk.adReward"] = { ru = "Награда за рекламу ×{1}", en = "Ad reward ×{1}", es = "Recompensa de anuncio ×{1}", pt = "Recompensa de anúncio ×{1}" },
	["perk.obstacleTime"] = { ru = "+{1} сек на полосе", en = "+{1}s on courses", es = "+{1}s en circuitos", pt = "+{1}s nos circuitos" },
	["perk.classCapacity"] = { ru = "+{1} мест в классе", en = "+{1} class seats", es = "+{1} plazas de clase", pt = "+{1} vagas na turma" },
	["perk.lessonSlots"] = { ru = "+{1} урок в день", en = "+{1} lessons a day", es = "+{1} lecciones al día", pt = "+{1} aulas por dia" },
	["perk.attemptRefund"] = { ru = "+{1} попытка в день", en = "+{1} retries a day", es = "+{1} reintentos al día", pt = "+{1} tentativas por dia" },
	["campus.title"] = { ru = "Кампус", en = "Campus", es = "Campus", pt = "Campus" },
	["campus.term"] = { ru = "Идёт семестр", en = "Term in progress", es = "Semestre en curso", pt = "Semestre em andamento" },
	["campus.campaign"] = { ru = "Выдвижение кандидатов", en = "Nominations open", es = "Candidaturas abiertas", pt = "Candidaturas abertas" },
	["campus.voting"] = { ru = "Голосование", en = "Voting", es = "Votación", pt = "Votação" },
	["campus.calendar"] = {
		ru = "{1} четверть, неделя {2} из {3}",
		en = "term {1}, week {2} of {3}",
		es = "trimestre {1}, semana {2} de {3}",
		pt = "trimestre {1}, semana {2} de {3}",
	},
	["campus.testWeek"] = { ru = "{1} · контрольная неделя ×1.2", en = "{1} · test week ×1.2", es = "{1} · semana de exámenes ×1.2", pt = "{1} · semana de provas ×1.2" },
	["campus.director"] = { ru = "Директор: {1}", en = "Director: {1}", es = "Director: {1}", pt = "Diretor: {1}" },
	["campus.noDirector"] = {
		ru = "Директора нет — кампус ждёт выборов",
		en = "No director — the campus is waiting on an election",
		es = "Sin director — el campus espera elecciones",
		pt = "Sem diretor — o campus aguarda eleição",
	},
	["campus.subjectOfMonth"] = { ru = "предмет месяца: {1}", en = "subject of the month: {1}", es = "materia del mes: {1}", pt = "matéria do mês: {1}" },
	["campus.eventRunning"] = { ru = "идёт школьное событие", en = "a school event is running", es = "hay un evento escolar", pt = "há um evento escolar" },
	["campus.daysLeft"] = { ru = "до конца срока {1} дн.", en = "{1} days left in the term", es = "quedan {1} días de mandato", pt = "faltam {1} dias de mandato" },
	["campus.stand"] = { ru = "Выдвинуть свою кандидатуру", en = "Put yourself forward", es = "Presentar tu candidatura", pt = "Apresentar sua candidatura" },
	["campus.standButton"] = { ru = "Выдвинуться", en = "Stand", es = "Presentarse", pt = "Candidatar-se" },
	["campus.votes"] = { ru = "{1} — {2} голосов", en = "{1} — {2} votes", es = "{1} — {2} votos", pt = "{1} — {2} votos" },
	["campus.vote"] = { ru = "Голос", en = "Vote", es = "Votar", pt = "Votar" },
	["campus.noCandidates"] = { ru = "Кандидатов пока нет.", en = "No candidates yet.", es = "Aún no hay candidatos.", pt = "Ainda não há candidatos." },
	["campus.event"] = { ru = "Школьное событие · осталось {1}", en = "School event · {1} left", es = "Evento escolar · quedan {1}", pt = "Evento escolar · restam {1}" },
	["campus.launch"] = { ru = "Запустить", en = "Launch", es = "Lanzar", pt = "Lançar" },
	["campus.pickSubject"] = { ru = "Предмет месяца (×1.5 всем)", en = "Subject of the month (×1.5 for everyone)", es = "Materia del mes (×1.5 para todos)", pt = "Matéria do mês (×1.5 para todos)" },
	["campus.motto"] = { ru = "Девиз школы", en = "School motto", es = "Lema de la escuela", pt = "Lema da escola" },
	["campus.deans"] = { ru = "Завучи — {1}", en = "Deans — {1}", es = "Decanos — {1}", pt = "Coordenadores — {1}" },

	["motto.learnTogether"] = { ru = "Учимся вместе", en = "We learn together", es = "Aprendemos juntos", pt = "Aprendemos juntos" },
	["motto.noOneLeftBehind"] = { ru = "Никого не бросаем", en = "Nobody left behind", es = "Nadie se queda atrás", pt = "Ninguém fica para trás" },
	["motto.askWhy"] = { ru = "Спрашивай «почему»", en = "Ask why", es = "Pregunta por qué", pt = "Pergunte por quê" },
	["motto.tryAgain"] = { ru = "Попробуй ещё раз", en = "Try again", es = "Inténtalo otra vez", pt = "Tente de novo" },
	["motto.knowledgeIsPower"] = { ru = "Знание — сила", en = "Knowledge is power", es = "El saber es poder", pt = "O saber é poder" },
	["motto.everyDayCounts"] = { ru = "Каждый день важен", en = "Every day counts", es = "Cada día cuenta", pt = "Cada dia conta" },

	-- ---- live lessons ----
	["live.invite"] = {
		ru = "{1} начинает урок «{2}» — {3} вопросов",
		en = "{1} is starting «{2}» — {3} questions",
		es = "{1} empieza «{2}» — {3} preguntas",
		pt = "{1} está começando «{2}» — {3} questões",
	},
	["live.join"] = { ru = "Зайти на урок", en = "Join the lesson", es = "Unirse a la lección", pt = "Entrar na aula" },
	["live.waiting"] = { ru = "Урок вот-вот начнётся", en = "The lesson is about to start", es = "La lección va a empezar", pt = "A aula vai começar" },
	["live.waitingBody"] = {
		ru = "Преподаватель сейчас задаст первый вопрос.",
		en = "Your teacher is about to ask the first question.",
		es = "El profesor hará la primera pregunta.",
		pt = "O professor vai fazer a primeira pergunta.",
	},
	["live.received"] = {
		ru = "Ответ принят. Ждём остальных.",
		en = "Answer in. Waiting for the rest.",
		es = "Respuesta recibida. Esperando al resto.",
		pt = "Resposta recebida. Aguardando os demais.",
	},
	["live.reveal"] = { ru = "Показать ответ", en = "Reveal answer", es = "Mostrar respuesta", pt = "Mostrar resposta" },
	["live.waitingRoom"] = { ru = "«{1}» · ждём учеников", en = "«{1}» · waiting for students", es = "«{1}» · esperando alumnos", pt = "«{1}» · esperando alunos" },
	["live.answeredCount"] = {
		ru = "Вопрос {1} из {2} · ответили {3} из {4}",
		en = "Question {1} of {2} · {3} of {4} answered",
		es = "Pregunta {1} de {2} · {3} de {4} respondieron",
		pt = "Questão {1} de {2} · {3} de {4} responderam",
	},
	["live.revealed"] = { ru = "Ответ показан · вопрос {1}", en = "Answer shown · question {1}", es = "Respuesta mostrada · pregunta {1}", pt = "Resposta mostrada · questão {1}" },
	["live.result"] = {
		ru = "Верно {1} из {2}\n+{3} баллов, из них {4} за живой урок",
		en = "{1} of {2} right\n+{3} points, {4} of them for the live lesson",
		es = "{1} de {2} correctas\n+{3} puntos, {4} por la clase en vivo",
		pt = "{1} de {2} certas\n+{3} pontos, {4} deles pela aula ao vivo",
	},

	-- ---- authoring ----
	["authoring.title"] = { ru = "Свой вопрос", en = "Your own question", es = "Tu propia pregunta", pt = "Sua própria questão" },
	["authoring.hint"] = {
		ru = "Вопрос до {1} символов, четыре варианта примерно одной длины, объяснение от {2} символов. Объяснение — это то, ради чего всё; оно показывается после ответа, верного или нет.",
		en = "Up to {1} characters, four options of roughly equal length, an explanation of at least {2}. The explanation is the whole point — it is shown after the answer, right or wrong.",
		es = "Hasta {1} caracteres, cuatro opciones de largo parecido, una explicación de al menos {2}. La explicación es lo importante: se muestra tras responder, sea correcto o no.",
		pt = "Até {1} caracteres, quatro opções de tamanho parecido, uma explicação de pelo menos {2}. A explicação é o que importa — ela aparece depois da resposta, certa ou errada.",
	},
	["authoring.stemPlaceholder"] = { ru = "текст вопроса", en = "question text", es = "texto de la pregunta", pt = "texto da questão" },
	["authoring.optionPlaceholder"] = { ru = "вариант {1}", en = "option {1}", es = "opción {1}", pt = "opção {1}" },
	["authoring.explanationPlaceholder"] = {
		ru = "объяснение — почему этот ответ верный",
		en = "explanation — why this answer is right",
		es = "explicación — por qué es correcta",
		pt = "explicação — por que está correta",
	},
	["authoring.empty"] = { ru = "Своих вопросов пока нет.", en = "No questions of your own yet.", es = "Aún no tienes preguntas propias.", pt = "Ainda sem questões próprias." },
	["authoring.sent"] = {
		ru = "Отправлено. Появится после проверки.",
		en = "Sent. It appears once it clears review.",
		es = "Enviado. Aparecerá tras la revisión.",
		pt = "Enviado. Aparece depois da revisão.",
	},
	["authoring.pending"] = { ru = "на проверке", en = "in review", es = "en revisión", pt = "em revisão" },
	["authoring.published"] = { ru = "опубликован", en = "published", es = "publicada", pt = "publicada" },
	["authoring.rejected"] = { ru = "отклонён", en = "rejected", es = "rechazada", pt = "rejeitada" },
	["authoring.pendingMeta"] = {
		ru = "{1} · {2} кл. · выйдет через {3} мин",
		en = "{1} · grade {2} · live in {3} min",
		es = "{1} · grado {2} · en {3} min",
		pt = "{1} · série {2} · em {3} min",
	},

	-- ---- shop ----
	["shop.title"] = { ru = "Магазин", en = "Shop", es = "Tienda", pt = "Loja" },
	["shop.passes"] = { ru = "Пропуска", en = "Passes", es = "Pases", pt = "Passes" },
	["shop.products"] = { ru = "Расходники", en = "Consumables", es = "Consumibles", pt = "Consumíveis" },
	["shop.ads"] = { ru = "За рекламу", en = "For an ad", es = "Por un anuncio", pt = "Por um anúncio" },
	["shop.owned"] = { ru = "Куплено", en = "Owned", es = "Comprado", pt = "Comprado" },
	["shop.buy"] = { ru = "Купить", en = "Buy", es = "Comprar", pt = "Comprar" },
	["shop.watch"] = { ru = "Смотреть", en = "Watch", es = "Ver", pt = "Assistir" },
	["shop.notConfigured"] = { ru = "не настроено", en = "not set up", es = "sin configurar", pt = "não configurado" },
	["shop.balance"] = { ru = "Баллов: {1}", en = "Points: {1}", es = "Puntos: {1}", pt = "Pontos: {1}" },
	["shop.usedToday"] = { ru = "сегодня {1} из {2}", en = "{1} of {2} today", es = "{1} de {2} hoy", pt = "{1} de {2} hoje" },
	["shop.cooldown"] = { ru = "через {1} мин", en = "in {1} min", es = "en {1} min", pt = "em {1} min" },
	["shop.noAds"] = {
		ru = "Сейчас нечего смотреть.",
		en = "Nothing to watch right now.",
		es = "Nada que ver ahora mismo.",
		pt = "Nada para assistir agora.",
	},

	-- ---- passes and products ----
	["pass.xp2"] = { ru = "Двойной опыт навсегда", en = "Double XP forever", es = "Doble experiencia para siempre", pt = "Experiência dobrada para sempre" },
	["pass.hint"] = { ru = "Подсказка в каждом тесте", en = "A hint in every test", es = "Una pista en cada prueba", pt = "Uma dica em cada teste" },
	["pass.lessonSlots"] = { ru = "Больше уроков в день", en = "More lessons per day", es = "Más lecciones al día", pt = "Mais aulas por dia" },
	["pass.autoNotes"] = { ru = "Конспект пишется сам", en = "Notes write themselves", es = "Apuntes automáticos", pt = "Anotações automáticas" },
	["pass.uniform"] = { ru = "Премиальная форма", en = "Premium uniform", es = "Uniforme premium", pt = "Uniforme premium" },
	["pass.classCapacity"] = { ru = "+10 мест в классе", en = "+10 seats in your class", es = "+10 plazas en tu clase", pt = "+10 vagas na sua turma" },
	["pass.secondClass"] = { ru = "Второй класс", en = "A second class", es = "Una segunda clase", pt = "Uma segunda turma" },
	["pass.listingPriority"] = { ru = "Выше в списке классов", en = "Higher in the class list", es = "Más arriba en la lista", pt = "Mais acima na lista" },
	["pass.prefabPack"] = { ru = "Больше деталей для полос", en = "More obstacle parts", es = "Más piezas de circuito", pt = "Mais peças de percurso" },

	["product.restoreAttempt"] = { ru = "Вернуть попытку", en = "Restore an attempt", es = "Recuperar un intento", pt = "Recuperar uma tentativa" },
	["product.xp3Boost"] = { ru = "Тройной опыт на 20 минут", en = "Triple XP for 20 minutes", es = "Triple experiencia 20 minutos", pt = "Experiência triplicada por 20 min" },
	["product.classPromoHour"] = { ru = "Продвинуть класс на час", en = "Promote your class for an hour", es = "Promocionar tu clase una hora", pt = "Promover sua turma por uma hora" },
	["product.extraTestSlot"] = { ru = "Ещё один тест", en = "One more test", es = "Una prueba más", pt = "Mais um teste" },

	["ad.doubleLessonReward"] = { ru = "Двойная награда за урок", en = "Double the lesson reward", es = "Doble recompensa por lección", pt = "Recompensa dobrada pela aula" },
	["ad.extraAttempt"] = { ru = "Дополнительная попытка", en = "An extra attempt", es = "Un intento extra", pt = "Uma tentativa extra" },
	["ad.skipCooldown"] = { ru = "Сбросить ожидание", en = "Skip the wait", es = "Saltar la espera", pt = "Pular a espera" },
	["ad.doubleOfflineNotes"] = { ru = "Удвоить накопленное", en = "Double what you banked", es = "Duplicar lo acumulado", pt = "Dobrar o acumulado" },
	["ad.promoteClass"] = { ru = "Продвинуть класс", en = "Promote your class", es = "Promocionar tu clase", pt = "Promover sua turma" },
	["ad.teacherTestSlot"] = { ru = "Ещё один слот теста", en = "One more test slot", es = "Otra ranura de prueba", pt = "Mais um espaço de teste" },

	-- ---- moderation ----
	["review.queue"] = { ru = "На проверке: {1}", en = "In review: {1}", es = "En revisión: {1}", pt = "Em revisão: {1}" },
	["review.none"] = { ru = "Проверять нечего.", en = "Nothing to review.", es = "Nada que revisar.", pt = "Nada para revisar." },
	["review.approve"] = { ru = "Пропустить", en = "Approve", es = "Aprobar", pt = "Aprovar" },
	["review.reject"] = { ru = "Отклонить", en = "Reject", es = "Rechazar", pt = "Rejeitar" },
	["review.answer"] = { ru = "Ответ: {1}", en = "Answer: {1}", es = "Respuesta: {1}", pt = "Resposta: {1}" },
	["review.done"] = { ru = "Решение принято", en = "Decision recorded", es = "Decisión registrada", pt = "Decisão registrada" },
	["review.deanOf"] = { ru = "Ты завуч: {1}", en = "You are dean of: {1}", es = "Eres decano de: {1}", pt = "Você é coordenador de: {1}" },

	-- ---- refusals ----
	--
	-- Keyed by the reason code the server returns, so a new refusal on the server
	-- shows up here as a visible `error.somethingNew` rather than as silence.
	["error.notLicensed"] = { ru = "Нужна лицензия преподавателя", en = "You need a teaching licence", es = "Necesitas licencia de profesor", pt = "Você precisa de licença de professor" },
	["error.classLimit"] = { ru = "Больше классов без пропуска нельзя", en = "No more classes without a pass", es = "No más clases sin un pase", pt = "Sem mais turmas sem um passe" },
	["error.titleRejected"] = { ru = "Название не прошло фильтр", en = "That name didn't clear the filter", es = "Ese nombre no pasó el filtro", pt = "Esse nome não passou no filtro" },
	["error.unknownSubject"] = { ru = "Нет такого предмета", en = "No such subject", es = "No existe esa materia", pt = "Matéria inexistente" },
	["error.full"] = { ru = "В классе нет мест", en = "The class is full", es = "La clase está llena", pt = "A turma está cheia" },
	["error.ownClass"] = { ru = "Нельзя учиться в своём классе", en = "You can't study in your own class", es = "No puedes estudiar en tu propia clase", pt = "Você não pode estudar na sua turma" },
	["error.notEnrolled"] = { ru = "Сначала вступи в класс", en = "Join the class first", es = "Únete a la clase primero", pt = "Entre na turma primeiro" },
	["error.noClass"] = { ru = "Класс не найден", en = "Class not found", es = "Clase no encontrada", pt = "Turma não encontrada" },
	["error.storeFailed"] = { ru = "Не удалось сохранить, попробуй ещё раз", en = "Couldn't save — try again", es = "No se pudo guardar, inténtalo otra vez", pt = "Não deu para salvar, tente de novo" },
	["error.leaveFailed"] = { ru = "Не вышло покинуть прошлый класс", en = "Couldn't leave your old class", es = "No se pudo salir de tu clase anterior", pt = "Não deu para sair da turma anterior" },
	["error.badGrade"] = { ru = "Класс — число от 1 до 11", en = "Grade must be 1 to 11", es = "El grado va de 1 a 11", pt = "A série vai de 1 a 11" },
	["error.cannotGraduate"] = { ru = "Выпускной ещё не заслужен", en = "Graduation isn't earned yet", es = "Aún no te has graduado", pt = "A formatura ainda não foi conquistada" },
	["error.gradeOutOfWindow"] = { ru = "Можно только ±1 класс от своего", en = "Only one grade either side of your class", es = "Solo un grado arriba o abajo", pt = "Apenas uma série acima ou abaixo" },
	["error.tooShort"] = { ru = "Слишком короткая полоса для этого класса", en = "Too short a course for that grade", es = "Circuito demasiado corto para ese grado", pt = "Percurso curto demais para essa série" },
	["error.tooLong"] = { ru = "Слишком длинная полоса", en = "That course is too long", es = "Ese circuito es demasiado largo", pt = "Esse percurso é longo demais" },
	["error.tooRepetitive"] = { ru = "Слишком однообразно — добавь разных модулей", en = "Too samey — mix in other modules", es = "Muy repetitivo — mezcla otros módulos", pt = "Repetitivo demais — misture outros módulos" },
	["error.moduleTooAdvanced"] = { ru = "Этот модуль недоступен на таком классе", en = "That module isn't available at this grade", es = "Ese módulo no está en este grado", pt = "Esse módulo não existe nesta série" },
	["error.wrongSubject"] = { ru = "Не тот предмет для этого задания", en = "Wrong subject for that", es = "Materia equivocada para eso", pt = "Matéria errada para isso" },
	["error.alreadyRunning"] = { ru = "Ты уже проходишь полосу", en = "You're already on a course", es = "Ya estás en un circuito", pt = "Você já está num percurso" },
	["error.notCampaign"] = { ru = "Выдвигаться можно только в дни выдвижения", en = "Nominations aren't open", es = "Las candidaturas están cerradas", pt = "As candidaturas estão fechadas" },
	["error.notVoting"] = { ru = "Голосование ещё не началось", en = "Voting hasn't opened", es = "La votación no ha empezado", pt = "A votação ainda não abriu" },
	["error.notEnoughRatings"] = { ru = "Нужно больше оценок от учеников", en = "You need more student ratings", es = "Necesitas más valoraciones", pt = "Você precisa de mais avaliações" },
	["error.ratingTooLow"] = { ru = "Рейтинг слишком низкий", en = "Your rating is too low", es = "Tu valoración es muy baja", pt = "Sua avaliação está baixa" },
	["error.termLimit"] = { ru = "Два срока подряд — предел", en = "Two consecutive terms is the limit", es = "Dos mandatos seguidos es el límite", pt = "Dois mandatos seguidos é o limite" },
	["error.notEligible"] = { ru = "Нужен аккаунт от недели и полчаса игры", en = "You need a week-old account and half an hour played", es = "Necesitas una cuenta de una semana y media hora jugada", pt = "É preciso conta de uma semana e meia hora jogada" },
	["error.notDirector"] = { ru = "Только директор кампуса", en = "Only the campus director", es = "Solo el director del campus", pt = "Apenas o diretor do campus" },
	["error.noEventsLeft"] = { ru = "События на этот срок закончились", en = "No events left this term", es = "No quedan eventos este mandato", pt = "Sem eventos neste mandato" },
	["error.noCandidate"] = { ru = "Такого кандидата нет", en = "No such candidate", es = "No existe ese candidato", pt = "Candidato inexistente" },
	["error.notDean"] = { ru = "Только завуч этого предмета", en = "Only the dean of that subject", es = "Solo el decano de esa materia", pt = "Apenas o coordenador dessa matéria" },
	["error.stemTooShort"] = { ru = "Вопрос слишком короткий", en = "The question is too short", es = "La pregunta es muy corta", pt = "A questão está curta demais" },
	["error.stemTooLong"] = { ru = "Вопрос слишком длинный", en = "The question is too long", es = "La pregunta es muy larga", pt = "A questão está longa demais" },
	["error.optionCount"] = { ru = "Нужно ровно четыре варианта", en = "Exactly four options", es = "Exactamente cuatro opciones", pt = "Exatamente quatro opções" },
	["error.badAnswer"] = { ru = "Отметь верный вариант", en = "Mark the right option", es = "Marca la opción correcta", pt = "Marque a opção correta" },
	["error.emptyOption"] = { ru = "Один из вариантов пустой", en = "One option is empty", es = "Una opción está vacía", pt = "Uma opção está vazia" },
	["error.optionTooLong"] = { ru = "Вариант слишком длинный", en = "That option is too long", es = "Esa opción es muy larga", pt = "Essa opção é longa demais" },
	["error.duplicateOption"] = { ru = "Два варианта совпадают", en = "Two options are the same", es = "Dos opciones son iguales", pt = "Duas opções são iguais" },
	["error.lopsidedOptions"] = { ru = "Один вариант заметно длиннее — по нему угадают", en = "One option is much longer — they'll guess it", es = "Una opción es mucho más larga — la adivinarán", pt = "Uma opção é bem maior — vão adivinhar" },
	["error.explanationTooShort"] = { ru = "Объяснение слишком короткое", en = "The explanation is too short", es = "La explicación es muy corta", pt = "A explicação está curta demais" },
	["error.explanationTooLong"] = { ru = "Объяснение слишком длинное", en = "The explanation is too long", es = "La explicación es muy larga", pt = "A explicação está longa demais" },
	["error.textRejected"] = { ru = "Текст не прошёл фильтр", en = "The text didn't clear the filter", es = "El texto no pasó el filtro", pt = "O texto não passou no filtro" },
	["error.authoredLimit"] = { ru = "Слишком много своих вопросов", en = "Too many questions of your own", es = "Demasiadas preguntas propias", pt = "Questões próprias demais" },
	["error.authoringDisabled"] = { ru = "Свои вопросы сейчас отключены", en = "Writing your own questions is off", es = "Escribir preguntas propias está desactivado", pt = "Escrever perguntas próprias está desativado" },
	["error.notOwner"] = { ru = "Это не твой класс", en = "That isn't your class", es = "Esa no es tu clase", pt = "Essa não é sua turma" },
	["error.notALiveLesson"] = { ru = "Живьём можно вести только тест", en = "Only a quiz can be taught live", es = "Solo se puede dar un test en vivo", pt = "Só um teste pode ser dado ao vivo" },
	["error.alreadyLive"] = { ru = "Урок уже идёт", en = "A lesson is already running", es = "Ya hay una lección en curso", pt = "Já há uma aula em andamento" },
	["error.noSession"] = { ru = "Урок уже закончился", en = "That lesson has ended", es = "Esa lección ya terminó", pt = "Essa aula já acabou" },
	["error.alreadyInLesson"] = { ru = "Ты уже на уроке", en = "You're already in a lesson", es = "Ya estás en una lección", pt = "Você já está numa aula" },
	["error.teacherLeft"] = { ru = "Преподаватель вышел", en = "The teacher left", es = "El profesor se fue", pt = "O professor saiu" },
	["error.teacherEnded"] = { ru = "Преподаватель закончил урок", en = "The teacher ended the lesson", es = "El profesor terminó la lección", pt = "O professor encerrou a aula" },
} :: { [string]: Bundle }

--- Returns the string for `key` in `locale`, with `{n}` replaced positionally.
---
--- An unknown key returns the key itself rather than an empty string. A visible
--- `class.missingThing` in the interface is a bug report; a blank space is a
--- mystery.
function Strings.get(key: string, locale: string, ...): string
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
			-- Leave an unfilled placeholder visible rather than blanking it: a
			-- literal {3} on screen says which translation has an argument the
			-- caller never passed.
			return "{" .. index .. "}"
		end
		return tostring(values[position])
	end)
	return result
end

return Strings
