package ch.unisg.scs;

import org.apache.kafka.clients.producer.RoundRobinPartitioner;
import org.apache.kafka.common.Cluster;
import org.apache.kafka.common.InvalidRecordException;

public class CustomPartitioner extends RoundRobinPartitioner {


    @Override
    public int partition(String topic, Object key, byte[] keyBytes, Object value, byte[] valueBytes, Cluster cluster) {


        if ((keyBytes == null) || (!(key instanceof String))) {
            throw new InvalidRecordException("All messages should have a valid key");
        }


        return Integer.valueOf((String) key);

    }

    @Override
    public void close() {

    }


}