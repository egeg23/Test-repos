--!strict
--- The parts a student can put into an assembly task.
---
--- Assembly is the science and art counterpart to PE's obstacle courses: a
--- lesson built entirely out of a fixed catalogue, so it carries no free text and
--- needs no moderation. What a student assembles is checked against an answer
--- that came with the task, not against something a teacher asserted -- a teacher
--- who could define which wiring is correct could teach that it is the wrong one.

local Components = {}

export type Component = {
	id: string,
	subject: string,
	displayKey: string,
}

Components.List = {
	{ id = "battery", subject = "science", displayKey = "component.battery" },
	{ id = "wire", subject = "science", displayKey = "component.wire" },
	{ id = "lamp", subject = "science", displayKey = "component.lamp" },
	{ id = "switch", subject = "science", displayKey = "component.switch" },
	{ id = "resistor", subject = "science", displayKey = "component.resistor" },
	{ id = "magnet", subject = "science", displayKey = "component.magnet" },
	{ id = "thermometer", subject = "science", displayKey = "component.thermometer" },
	{ id = "beaker", subject = "science", displayKey = "component.beaker" },
	{ id = "funnel", subject = "science", displayKey = "component.funnel" },
	{ id = "filter", subject = "science", displayKey = "component.filter" },
	{ id = "seed", subject = "science", displayKey = "component.seed" },
	{ id = "soil", subject = "science", displayKey = "component.soil" },
	{ id = "water", subject = "science", displayKey = "component.water" },
	{ id = "sunlight", subject = "science", displayKey = "component.sunlight" },
	{ id = "sprout", subject = "science", displayKey = "component.sprout" },

	{ id = "red", subject = "art", displayKey = "component.red" },
	{ id = "blue", subject = "art", displayKey = "component.blue" },
	{ id = "yellow", subject = "art", displayKey = "component.yellow" },
	{ id = "green", subject = "art", displayKey = "component.green" },
	{ id = "orange", subject = "art", displayKey = "component.orange" },
	{ id = "purple", subject = "art", displayKey = "component.purple" },
	{ id = "sky", subject = "art", displayKey = "component.sky" },
	{ id = "horizon", subject = "art", displayKey = "component.horizon" },
	{ id = "foreground", subject = "art", displayKey = "component.foreground" },
	{ id = "shadow", subject = "art", displayKey = "component.shadow" },
	{ id = "highlight", subject = "art", displayKey = "component.highlight" },
} :: { Component }

--- Slots per task. Fewer than three is not an assembly, more than six is a chore.
Components.MinSlots = 3
Components.MaxSlots = 6
--- Spare pieces in the palette beyond the ones actually needed. Without
--- distractors a task with four slots and four pieces solves itself.
Components.MinDistractors = 2

local byId: { [string]: Component } = {}
for _, entry in Components.List do
	byId[entry.id] = entry
end

function Components.get(id: string): Component?
	return byId[id]
end

function Components.belongsTo(id: string, subject: string): boolean
	local entry = byId[id]
	return entry ~= nil and entry.subject == subject
end

return Components
