package ch.unisg.scs.edpo.kafkastreams.domain;

// Result of joining a detected block with its classified color.
// Written to inventory.blocks.v1 and materialized in the inventory KTable.
// Key: cubeId
public record BlockColorEvent(
        String cubeId,
        BlockColor color,
        long detectedAt
) {}
