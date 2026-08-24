--!strict
--- Per-player token buckets for remote traffic.
---
--- Every remote is reachable from an exploiting client at whatever rate they
--- like, so each one is metered. Buckets are dropped when a player leaves, which
--- is also what stops this table growing for the life of the server.

local Players = game:GetService("Players")

local RateLimiter = {}

type Bucket = {
	tokens: number,
	capacity: number,
	refillPerSecond: number,
	lastRefill: number,
}

local buckets: { [Player]: { [string]: Bucket } } = {}

Players.PlayerRemoving:Connect(function(player: Player)
	buckets[player] = nil
end)

--- Returns true when the call is allowed and consumes a token.
function RateLimiter.consume(
	player: Player,
	key: string,
	capacity: number,
	refillPerSecond: number
): boolean
	local playerBuckets = buckets[player]
	if playerBuckets == nil then
		playerBuckets = {}
		buckets[player] = playerBuckets
	end

	local now = os.clock()
	local bucket = playerBuckets[key]
	if bucket == nil then
		bucket = {
			tokens = capacity,
			capacity = capacity,
			refillPerSecond = refillPerSecond,
			lastRefill = now,
		}
		playerBuckets[key] = bucket
	end

	local elapsed = now - bucket.lastRefill
	bucket.lastRefill = now
	bucket.tokens = math.min(bucket.capacity, bucket.tokens + elapsed * bucket.refillPerSecond)

	if bucket.tokens < 1 then
		return false
	end
	bucket.tokens -= 1
	return true
end

return RateLimiter
