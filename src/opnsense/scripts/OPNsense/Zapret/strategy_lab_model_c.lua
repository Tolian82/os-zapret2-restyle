-- Strategy Lab Model C selector.
--
-- Each candidate action chain is preceded by zapret-auto.lua's `condition` orchestrator.
-- This iff function selects the chain by the controlled client source port. It fails
-- closed when packet metadata or selector arguments are missing or invalid.

local function strategy_lab_model_c_port_matches(value, observed)
    if type(value) ~= "string" or type(observed) ~= "number" then
        return false
    end
    for token in string.gmatch(value, "[^,]+") do
        local port = tonumber(token)
        if port and port == observed then
            return true
        end
    end
    return false
end

function strategy_lab_model_c_source_port(desync)
    if type(desync) ~= "table" or type(desync.arg) ~= "table" then
        return false
    end
    if type(desync.dis) ~= "table" or type(desync.dis.tcp) ~= "table" then
        return false
    end

    local tcp = desync.dis.tcp
    local observed
    if desync.outgoing == false then
        observed = tonumber(tcp.th_dport)
    else
        observed = tonumber(tcp.th_sport)
    end
    if not observed then
        return false
    end
    return strategy_lab_model_c_port_matches(desync.arg.source_ports, observed)
end
