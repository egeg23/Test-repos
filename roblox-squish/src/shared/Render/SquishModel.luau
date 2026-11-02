--!strict
--- Builds the model for a squish.
---
--- If ReplicatedStorage.SquishMeshes holds a MeshPart named after the species
--- (imported in Studio from assets/meshes, see the README), that is cloned and
--- scaled. Otherwise the squish is assembled from primitive parts: an ellipsoid
--- body, a face, and a few shape-specific pieces. The primitive version is
--- deliberately simple -- soft colours, round forms, a dot-eyed face -- so the
--- game looks finished enough to play before any mesh is uploaded.
---
--- Used by the server for shelves and carried squishes, and by the client for
--- the unbox reveal. Pure construction: nothing here is networked or stateful.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Squishes = require(script.Parent.Parent.Config.Squishes)

local SquishModel = {}

--- Base body size at tier 1, in studs. Each tier adds a quarter, so a tier-5
--- squish is twice as big as a tier-1 and reads as "merged" from across a base.
SquishModel.BaseSize = 2.4
SquishModel.GrowthPerTier = 0.25

local EYE = Color3.fromRGB(60, 46, 58)
local BLUSH = Color3.fromRGB(255, 170, 190)

local function rgb(triple: { number }): Color3
	return Color3.fromRGB(triple[1], triple[2], triple[3])
end

function SquishModel.sizeFor(tier: number): number
	return SquishModel.BaseSize * (1 + SquishModel.GrowthPerTier * (tier - 1))
end

type Builder = {
	model: Model,
	body: BasePart,
	unit: number,
	part: (self: Builder, name: string, shape: string, size: Vector3, offset: Vector3, colour: Color3) -> BasePart,
}

local function newBuilder(model: Model, body: BasePart, unit: number): Builder
	local builder = {} :: any
	builder.model = model
	builder.body = body
	builder.unit = unit
	function builder.part(self: Builder, name: string, shape: string, size: Vector3, offset: Vector3, colour: Color3): BasePart
		local p = Instance.new("Part")
		p.Name = name
		p.Size = size * self.unit
		p.Color = colour
		p.Material = Enum.Material.SmoothPlastic
		p.TopSurface = Enum.SurfaceType.Smooth
		p.BottomSurface = Enum.SurfaceType.Smooth
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.Massless = true
		p.Anchored = false
		if shape == "ball" then
			local mesh = Instance.new("SpecialMesh")
			mesh.MeshType = Enum.MeshType.Sphere
			mesh.Parent = p
		elseif shape == "cylinder" then
			local mesh = Instance.new("SpecialMesh")
			mesh.MeshType = Enum.MeshType.Cylinder
			mesh.Parent = p
		end
		p.CFrame = self.body.CFrame * CFrame.new(offset * self.unit)
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = self.body
		weld.Part1 = p
		weld.Parent = p
		p.Parent = self.model
		return p
	end
	return builder :: Builder
end

--- A face on the front (-Z) of the body: two eyes and two blush marks.
local function face(b: Builder, height: number, depth: number, spread: number)
	for _, side in { -1, 1 } do
		b:part("Eye", "ball", Vector3.new(0.14, 0.18, 0.08), Vector3.new(side * spread, height, -depth), EYE)
		b:part("Blush", "ball", Vector3.new(0.2, 0.1, 0.05), Vector3.new(side * (spread + 0.14), height - 0.13, -depth + 0.02), BLUSH)
	end
	b:part("Smile", "ball", Vector3.new(0.12, 0.05, 0.05), Vector3.new(0, height - 0.12, -depth - 0.005), EYE)
end

local shapes: { [string]: (Builder, Color3, Color3) -> () } = {
	dumpling = function(b, _body, accent)
		b:part("Knot", "ball", Vector3.new(0.35, 0.3, 0.35), Vector3.new(0, 0.38, 0), accent)
		for i = 0, 5 do
			local angle = i * math.pi / 3
			b:part("Pleat", "ball", Vector3.new(0.12, 0.3, 0.12), Vector3.new(math.cos(angle) * 0.22, 0.3, math.sin(angle) * 0.22), accent)
		end
		face(b, 0.0, 0.47, 0.17)
	end,
	mochi = function(b, _body, accent)
		b:part("Dust", "ball", Vector3.new(0.7, 0.12, 0.7), Vector3.new(0, 0.32, 0), accent)
		face(b, 0.0, 0.48, 0.17)
	end,
	toast = function(b, _body, accent)
		b:part("Crust", "block", Vector3.new(1.02, 1.02, 0.36), Vector3.new(0, 0, 0.04), accent)
		b:part("Butter", "block", Vector3.new(0.3, 0.12, 0.25), Vector3.new(0, 0.55, -0.05), Color3.fromRGB(255, 240, 150))
		face(b, 0.05, 0.19, 0.16)
	end,
	boba = function(b, _body, accent)
		b:part("Lid", "ball", Vector3.new(0.95, 0.35, 0.95), Vector3.new(0, 0.5, 0), Color3.fromRGB(240, 230, 250))
		b:part("Straw", "block", Vector3.new(0.1, 0.5, 0.1), Vector3.new(0.15, 0.85, 0), Color3.fromRGB(170, 120, 220))
		for i = 0, 4 do
			b:part("Pearl", "ball", Vector3.new(0.14, 0.14, 0.14), Vector3.new(-0.3 + i * 0.15, -0.35, -0.42), accent)
		end
		face(b, 0.12, 0.47, 0.15)
	end,
	cloud = function(b, body, _accent)
		b:part("PuffL", "ball", Vector3.new(0.6, 0.55, 0.6), Vector3.new(-0.45, -0.1, 0), body)
		b:part("PuffR", "ball", Vector3.new(0.6, 0.55, 0.6), Vector3.new(0.45, -0.1, 0), body)
		face(b, 0.0, 0.48, 0.15)
	end,
	frog = function(b, body, accent)
		b:part("Belly", "ball", Vector3.new(0.6, 0.5, 0.2), Vector3.new(0, -0.15, -0.38), accent)
		for _, side in { -1, 1 } do
			b:part("EyeBump", "ball", Vector3.new(0.32, 0.3, 0.32), Vector3.new(side * 0.25, 0.42, -0.1), body)
			b:part("Eye", "ball", Vector3.new(0.13, 0.15, 0.06), Vector3.new(side * 0.25, 0.45, -0.26), EYE)
		end
		b:part("Smile", "ball", Vector3.new(0.3, 0.06, 0.05), Vector3.new(0, 0.12, -0.47), EYE)
	end,
	bao = function(b, _body, accent)
		for _, side in { -1, 1 } do
			b:part("Ear", "ball", Vector3.new(0.25, 0.25, 0.15), Vector3.new(side * 0.33, 0.42, 0), accent)
			b:part("Patch", "ball", Vector3.new(0.22, 0.26, 0.06), Vector3.new(side * 0.17, 0.02, -0.46), accent)
		end
		face(b, 0.02, 0.49, 0.17)
	end,
	pudding = function(b, _body, accent)
		b:part("Caramel", "cylinder", Vector3.new(0.18, 0.86, 0.86), Vector3.new(0, 0.5, 0), accent)
		b:part("Cherry", "ball", Vector3.new(0.22, 0.22, 0.22), Vector3.new(0, 0.66, 0), Color3.fromRGB(255, 120, 140))
		face(b, -0.05, 0.47, 0.16)
	end,
	taiyaki = function(b, body, accent)
		b:part("Tail", "block", Vector3.new(0.35, 0.6, 0.2), Vector3.new(0.75, 0, 0), accent)
		b:part("Fin", "ball", Vector3.new(0.3, 0.2, 0.15), Vector3.new(0, 0.4, 0), body)
		face(b, 0.05, 0.47, 0.13)
	end,
	macaron = function(b, body, accent)
		b:part("Filling", "cylinder", Vector3.new(0.16, 1.02, 1.02), Vector3.new(0, 0, 0), accent)
		b:part("Top", "ball", Vector3.new(1, 0.4, 1), Vector3.new(0, 0.22, 0), body)
		face(b, 0.2, 0.47, 0.15)
	end,
	dragon = function(b, body, accent)
		for _, side in { -1, 1 } do
			b:part("Wing", "ball", Vector3.new(0.45, 0.35, 0.1), Vector3.new(side * 0.5, 0.15, 0.25), accent)
			b:part("Horn", "ball", Vector3.new(0.1, 0.25, 0.1), Vector3.new(side * 0.18, 0.5, 0), accent)
		end
		b:part("Tail", "ball", Vector3.new(0.25, 0.25, 0.5), Vector3.new(0, -0.25, 0.5), body)
		face(b, 0.05, 0.48, 0.16)
	end,
	pumpkin = function(b, body, accent)
		for _, side in { -1, 1 } do
			b:part("Lobe", "ball", Vector3.new(0.5, 0.85, 0.85), Vector3.new(side * 0.3, 0, 0), body)
		end
		b:part("Stem", "block", Vector3.new(0.12, 0.25, 0.12), Vector3.new(0, 0.5, 0), accent)
		face(b, 0.0, 0.49, 0.17)
	end,
	dango = function(b, body, accent)
		b:part("Middle", "ball", Vector3.new(0.75, 0.7, 0.75), Vector3.new(0, -0.55, 0), accent)
		b:part("Bottom", "ball", Vector3.new(0.7, 0.65, 0.7), Vector3.new(0, -1.05, 0), body)
		b:part("Stick", "block", Vector3.new(0.08, 2.2, 0.08), Vector3.new(0, -0.5, 0), Color3.fromRGB(230, 200, 150))
		face(b, 0.0, 0.47, 0.15)
	end,
	sakura = function(b, _body, accent)
		for i = 0, 4 do
			local angle = i * 2 * math.pi / 5
			b:part("Petal", "ball", Vector3.new(0.22, 0.08, 0.3), Vector3.new(math.cos(angle) * 0.15, 0.48, math.sin(angle) * 0.15), accent)
		end
		face(b, 0.0, 0.48, 0.17)
	end,
	melon = function(b, _body, accent)
		b:part("Flesh", "cylinder", Vector3.new(0.12, 0.92, 0.92), Vector3.new(0, 0.25, 0), accent)
		for i = 0, 3 do
			b:part("Seed", "ball", Vector3.new(0.06, 0.05, 0.1), Vector3.new(-0.2 + i * 0.13, 0.32, 0.1 - (i % 2) * 0.15), EYE)
		end
		face(b, -0.1, 0.48, 0.16)
	end,
}

--- Proportions of the body for each shape, as a fraction of the unit size.
local bodyScale: { [string]: Vector3 } = {
	dumpling = Vector3.new(1, 0.8, 1),
	mochi = Vector3.new(1, 0.7, 1),
	toast = Vector3.new(0.95, 1, 0.3),
	boba = Vector3.new(0.85, 1.05, 0.85),
	cloud = Vector3.new(0.9, 0.8, 0.8),
	frog = Vector3.new(1, 0.8, 0.9),
	bao = Vector3.new(1, 0.85, 1),
	pudding = Vector3.new(0.9, 0.9, 0.9),
	taiyaki = Vector3.new(1.3, 0.8, 0.6),
	macaron = Vector3.new(1, 0.45, 1),
	dragon = Vector3.new(0.9, 0.9, 0.9),
	pumpkin = Vector3.new(0.8, 0.8, 0.85),
	dango = Vector3.new(0.75, 0.7, 0.75),
	sakura = Vector3.new(1, 0.85, 1),
	melon = Vector3.new(1, 0.55, 1),
}

--- A model whose pivot is the bottom of its body, so PivotTo onto the top of
--- a shelf stands it on the shelf rather than half inside it.
function SquishModel.build(speciesId: string, tier: number): Model
	local species = Squishes.get(speciesId)
	assert(species ~= nil, `unknown squish species {speciesId}`)
	local unit = SquishModel.sizeFor(tier)

	local model = Instance.new("Model")
	model.Name = speciesId
	model:SetAttribute("Species", speciesId)
	model:SetAttribute("Tier", tier)

	local folder = ReplicatedStorage:FindFirstChild("SquishMeshes")
	local mesh = if folder ~= nil then folder:FindFirstChild(speciesId) else nil
	if mesh ~= nil and mesh:IsA("BasePart") then
		local body = mesh:Clone()
		body.Name = "Body"
		local largest = math.max(body.Size.X, body.Size.Y, body.Size.Z)
		body.Size = body.Size * (unit / largest)
		body.Anchored = true
		body.CanCollide = true
		body.CFrame = CFrame.new(0, body.Size.Y / 2, 0)
		body.PivotOffset = CFrame.new(0, -body.Size.Y / 2, 0)
		body.Parent = model
		model.PrimaryPart = body
		return model
	end

	local scale = bodyScale[species.shape] or Vector3.new(1, 1, 1)
	local bodyColour = rgb(species.palette[1])
	local accent = rgb(species.palette[2] or species.palette[1])

	local body = Instance.new("Part")
	body.Name = "Body"
	body.Size = scale * unit
	body.Color = bodyColour
	body.Material = if species.shape == "dragon" then Enum.Material.Glass else Enum.Material.SmoothPlastic
	body.Transparency = if species.shape == "dragon" then 0.15 else 0
	body.TopSurface = Enum.SurfaceType.Smooth
	body.BottomSurface = Enum.SurfaceType.Smooth
	body.Anchored = true
	body.CanCollide = true
	-- Bouncy, so a squish that slips out of a thief's arms actually bounces.
	body.CustomPhysicalProperties = PhysicalProperties.new(0.4, 0.6, 0.85, 1, 1)
	if species.shape ~= "toast" then
		local sphere = Instance.new("SpecialMesh")
		sphere.MeshType = Enum.MeshType.Sphere
		sphere.Parent = body
	end
	body.CFrame = CFrame.new(0, body.Size.Y / 2, 0)
	body.PivotOffset = CFrame.new(0, -body.Size.Y / 2, 0)
	body.Parent = model
	model.PrimaryPart = body

	local build = shapes[species.shape]
	if build ~= nil then
		build(newBuilder(model, body, unit), bodyColour, accent)
	end
	-- Parts were placed relative to an anchored body; anchoring them too keeps a
	-- shelf model perfectly still until something unanchors the body.
	for _, child in model:GetChildren() do
		if child:IsA("BasePart") and child ~= body then
			child.Anchored = true
		end
	end
	return model
end

--- Anchors or frees the whole model. Free means physics: the body collides and
--- bounces, the decorations follow on their welds.
function SquishModel.setFree(model: Model, free: boolean)
	for _, child in model:GetDescendants() do
		if child:IsA("BasePart") then
			child.Anchored = not free
		end
	end
end

return SquishModel
