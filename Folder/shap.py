# import shap
# import xgboost as xgb
# import numpy as np

# X = np.random.rand(100,3)
# y = (X[:,0] + X[:,1] > 1).astype(int)

# model = xgb.XGBClassifier().fit(X, y)

# explainer = shap.TreeExplainer(model)
# shap_values = explainer.shap_values(X)

# shap.summary_plot(shap_values, X)





from lime import lime_tabular
explainer = lime_tabular.LimeTabularExplainer(
    X,
    feature_names=["income", "age", "debtratio"],
    class_names=["reject","approve"],
)

exp = explainer.explain_instance(X[0], model.predict_proba)
exp.show_in_notebook()
