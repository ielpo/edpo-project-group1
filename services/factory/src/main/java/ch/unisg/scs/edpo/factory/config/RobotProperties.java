package ch.unisg.scs.edpo.factory.config;

import jakarta.validation.constraints.NotNull;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.net.URI;

@Validated
@ConfigurationProperties(prefix = "edpo.robot")
public record RobotProperties(@NotNull RobotInventory inventory, @NotNull RobotFlows flows, @NotNull RobotAssembly assembly,
                              @NotNull RobotEndpoint right, RobotEndpoint left) {
}
