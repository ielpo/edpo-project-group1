package ch.unisg.scs.edpo.kafkastreams.domain;

public enum BlockColor {
    RED, GREEN, BLUE, YELLOW, UNKNOWN;

    // Heuristic RGB classification — thresholds need calibration against real sensor readings.
    // Yellow = high red + high green + low blue (additive color mixing).
    public static BlockColor from(int r, int g, int b) {
        int max = Math.max(r, Math.max(g, b));
        if (max < 30) return UNKNOWN;
        if (r > 150 && g > 150 && b < 100) return YELLOW;
        if (r >= max) return RED;
        if (g >= max) return GREEN;
        if (b >= max) return BLUE;
        return UNKNOWN;
    }
}
