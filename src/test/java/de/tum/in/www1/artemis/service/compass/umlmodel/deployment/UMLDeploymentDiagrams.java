package de.tum.in.www1.artemis.service.compass.umlmodel.deployment;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;

import org.apache.commons.io.IOUtils;

final class UMLDeploymentDiagrams {

    static final String DEPLOYMENT_MODEL_1;

    static final String DEPLOYMENT_MODEL_2;

    static final String DEPLOYMENT_MODEL_3;

    static {
        try {
            DEPLOYMENT_MODEL_1 = IOUtils.toString(UMLDeploymentDiagrams.class.getResource("deploymentModel1.json"), StandardCharsets.UTF_8);
            DEPLOYMENT_MODEL_2 = IOUtils.toString(UMLDeploymentDiagrams.class.getResource("deploymentModel2.json"), StandardCharsets.UTF_8);
            DEPLOYMENT_MODEL_3 = IOUtils.toString(UMLDeploymentDiagrams.class.getResource("deploymentModel3.json"), StandardCharsets.UTF_8);
        }
        catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private UMLDeploymentDiagrams() {
        // do not instantiate
    }
}
