package ch.unisg.scs.edpo.factory.adapters.out;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@RequiredArgsConstructor
@Component
@Slf4j
public class ControlRobotAdapter {
    private final Environment environment;


}
