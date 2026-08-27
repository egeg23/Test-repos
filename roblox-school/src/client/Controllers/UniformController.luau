--!strict
--- The premium uniform: the one thing in the shop that is only ever cosmetic.
---
--- Applied on the client, to the local player's own character. That is not a
--- shortcut -- a cosmetic written on the server would replicate, which is what
--- you want, but this one is drawn from a pass the server has already vouched
--- for in the `me` payload, and drawing it locally keeps a wardrobe change off
--- the network entirely. The cost is that other players do not see it, which is
--- the honest trade for v1 and is written on the tin: nothing about the uniform
--- affects anyone else's game.
---
--- If it ever needs to be visible to others, it moves to the server and becomes
--- a tagged accessory. Nothing else has to change.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local UniformController = {}

local player = Players.LocalPlayer

local BLAZER = Color3.fromRGB(46, 58, 104)
local TRIM = Color3.fromRGB(196, 164, 84)
local TIE = Color3.fromRGB(150, 46, 60)

local owned = false

--- Dresses a character. Idempotent: re-run on every respawn, and re-run when the
--- pass arrives, which may be either side of the character existing.
local function dress(character: Model)
	if not owned then
		return
	end
	if character:FindFirstChild("SchoolUniform") ~= nil then
		return
	end

	local torso = character:FindFirstChild("UpperTorso") or character:FindFirstChild("Torso")
	if torso == nil or not torso:IsA("BasePart") then
		return
	end

	local folder = Instance.new("Folder")
	folder.Name = "SchoolUniform"
	folder.Parent = character

	local function piece(name: string, size: Vector3, offset: CFrame, colour: Color3)
		local part = Instance.new("Part")
		part.Name = name
		part.Size = size
		part.Color = colour
		part.Material = Enum.Material.Fabric
		part.CanCollide = false
		part.CanQuery = false
		part.CanTouch = false
		part.Massless = true
		part.Parent = folder

		-- Welded rather than positioned: the torso moves every frame, and a part
		-- placed once would stay where the player was standing when it appeared.
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = torso :: BasePart
		weld.Part1 = part
		weld.Parent = part
		part.CFrame = (torso :: BasePart).CFrame * offset
		weld.Enabled = true
	end

	local depth = (torso :: BasePart).Size.Z
	piece("Blazer", (torso :: BasePart).Size + Vector3.new(0.08, 0.04, 0.08), CFrame.new(), BLAZER)
	piece("Tie", Vector3.new(0.25, 0.9, 0.08), CFrame.new(0, 0.1, -depth / 2 - 0.05), TIE)
	piece(
		"Trim",
		Vector3.new((torso :: BasePart).Size.X + 0.1, 0.1, depth + 0.1),
		CFrame.new(0, -(torso :: BasePart).Size.Y / 2 + 0.1, 0),
		TRIM
	)
end

local function dressCurrent()
	local character = player.Character
	if character ~= nil then
		dress(character)
	end
end

function UniformController.init()
	player.CharacterAdded:Connect(function(character: Model)
		-- The torso is not there the instant the character is, so the parts are
		-- welded once it appears rather than on a fixed delay.
		character:WaitForChild("HumanoidRootPart", 10)
		dress(character)
	end)

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action ~= "me" or not result.ok then
			return
		end
		local passes = result.payload.passes
		local nowOwned = typeof(passes) == "table" and passes.uniform == true
		if nowOwned and not owned then
			owned = true
			dressCurrent()
		end
	end)
end

return UniformController
