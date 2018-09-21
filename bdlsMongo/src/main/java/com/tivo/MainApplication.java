package com.tivo;

import com.mongodb.MongoClient;
import com.mongodb.client.FindIterable;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.Topology;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.HashSet;
import java.util.Properties;

public class MainApplication {

    private static final Logger gLogger = LoggerFactory.getLogger(MainApplication.class);
    public static String inputBroker = "core01.tpc1.tivo.com:9092";
    public static HashSet<String> bodyIds = new HashSet<>();
    public static MongoClient mongoClient;
    public static MongoDatabase db;
    public static MongoCollection<Document> bodyDataObjectLogCollection;

    public static void connectDb() {
        mongoClient = new MongoClient("0.0.0.0", 9000);
        db = mongoClient.getDatabase("kafkaDb");
        bodyDataObjectLogCollection = db.getCollection("recordingLog");
    }

    public static void main(String[] args) {
        try {
            gLogger.info("");

            connectDb();

            InputStream inputStream = MainApplication.class.getResourceAsStream("/tcds.txt");
            BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(inputStream, "UTF-8"));

            String line = "";
            while (true) {
                line = bufferedReader.readLine();
                if (line == null) {
                    break;
                }
                line = line.replaceAll("\\p{Z}", "");

                bodyIds.add(line);
                gLogger.info("TCD is: {}", line);
                line = "";
            }

            // Read topic names from the config
            String bodyDataObjectLogTopicProductionInput = "tpc1.production.frontend.bodyDataObjectLog";
            String bodyDataObjectLogTopicStagingInput = "tpc1.staging.frontend.bodyDataObjectLog";

            Topology builder = new Topology();

            builder.addSource("bodyDataObjectLog", bodyDataObjectLogTopicProductionInput, bodyDataObjectLogTopicStagingInput);
            builder.addProcessor("consumedProcessor", () -> new ConsumerProcessor(), "bodyDataObjectLog");

            Properties streamsConfiguration = new Properties();
            streamsConfiguration.setProperty(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, inputBroker);
            streamsConfiguration.setProperty(StreamsConfig.APPLICATION_ID_CONFIG, "bdlsMongo-tpc1");
            streamsConfiguration.setProperty(StreamsConfig.CLIENT_ID_CONFIG, "bdlsMongo-tpc1");
            streamsConfiguration.put(StreamsConfig.REPLICATION_FACTOR_CONFIG, "3");
            streamsConfiguration.setProperty(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass().getName());
            streamsConfiguration.setProperty(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.ByteArray().getClass().getName());

            KafkaStreams streams = new KafkaStreams(builder, streamsConfiguration);
            gLogger.info("STARTING APPLICATION");
            gLogger.info(String.valueOf(builder.describe()));
            //streams.cleanUp();
            streams.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
