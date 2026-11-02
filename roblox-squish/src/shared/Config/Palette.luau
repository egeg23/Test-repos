--!strict
--- The pastel palette everything is painted from: the bases, the plaza and the
--- interface. One place, so a colour pass is one file.

local Palette = {}

Palette.World = {
	ground = { 196, 236, 204 },
	plaza = { 255, 238, 214 },
	floor = { 255, 244, 236 },
	wall = { 255, 214, 228 },
	accent = { 214, 196, 255 },
	home = { 190, 236, 255 },
	path = { 246, 232, 214 },
	trap = { 236, 236, 246 },
	shelf = { 255, 255, 255 },
	machine = { 255, 196, 214 },
	stage = { 214, 236, 255 },
}

--- Each plot gets its own wall colour so a player knows their base from across
--- the map.
Palette.PlotWalls = {
	{ 255, 204, 222 },
	{ 204, 230, 255 },
	{ 214, 246, 204 },
	{ 255, 236, 190 },
	{ 230, 214, 255 },
	{ 255, 220, 200 },
}

Palette.Ui = {
	panel = { 255, 250, 252 },
	panelEdge = { 255, 214, 230 },
	ink = { 92, 70, 96 },
	muted = { 160, 140, 165 },
	button = { 255, 170, 200 },
	buttonInk = { 255, 255, 255 },
	good = { 130, 210, 160 },
	disabled = { 225, 218, 228 },
	ad = { 255, 196, 120 },
	coin = { 255, 200, 90 },
}

function Palette.colour(triple: { number }): Color3
	return Color3.fromRGB(triple[1], triple[2], triple[3])
end

return Palette
